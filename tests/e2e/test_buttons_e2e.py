import re, sys, json
from playwright.sync_api import sync_playwright, expect

URL = "http://127.0.0.1:5173/"
results = []
def check(name, ok, extra=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{extra}]" if extra else ""))

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1600, "height": 1000}, accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(URL)
    page.wait_for_selector("text=TWINEVAC", timeout=15000)
    page.wait_for_selector("text=Live Telemetry", timeout=10000)
    check("page loads + websocket live", True)

    # Reset first so the run is deterministic
    page.get_by_title("Reset to Initial Baseline").click()
    page.wait_for_timeout(500)

    # Run / Pause
    page.get_by_title("Start Simulation").click()
    page.wait_for_selector("button[title='Pause Simulation']", timeout=5000)
    check("Run Twin -> button becomes Pause", True)
    t1 = page.locator("text=/T\\+ [0-9.]+m/").first.inner_text()
    page.wait_for_timeout(3500)
    t2 = page.locator("text=/T\\+ [0-9.]+m/").first.inner_text()
    check("simulation clock advances while running", t1 != t2, f"{t1} -> {t2}")
    page.get_by_title("Pause Simulation").click()
    try:
        page.wait_for_selector("button[title='Start Simulation']", timeout=4000)
        check("Pause -> button returns to Run Twin (was stuck before)", True)
    except Exception:
        check("Pause -> button returns to Run Twin (was stuck before)", False)
    page.wait_for_timeout(1500)
    t3 = page.locator("text=/T\\+ [0-9.]+m/").first.inner_text()
    page.wait_for_timeout(2000)
    t4 = page.locator("text=/T\\+ [0-9.]+m/").first.inner_text()
    check("clock really stopped after Pause", t3 == t4, f"{t3} == {t4}")

    # Step
    step = page.get_by_title("Step Forward (+0.5 min)")
    before = page.locator("text=/T\\+ [0-9.]+m/").first.inner_text()
    step.click(); page.wait_for_timeout(600)
    after = page.locator("text=/T\\+ [0-9.]+m/").first.inner_text()
    check("Step advances the clock", before != after, f"{before} -> {after}")

    # Speed highlight while paused
    page.get_by_role("button", name="5x").click(); page.wait_for_timeout(800)
    cls = page.get_by_role("button", name="5x").get_attribute("class")
    check("5x speed highlights while paused", "bg-cyan-600" in cls)
    page.get_by_role("button", name="1x").click(); page.wait_for_timeout(800)
    check("1x speed highlights", "bg-cyan-600" in page.get_by_role("button", name="1x").get_attribute("class"))

    # Horizon tabs
    for label in ["+15 MIN", "+30 MIN", "+60 MIN", "NOW"]:
        page.get_by_role("button", name=re.compile(re.escape(label))).first.click()
    check("prediction horizon tabs click", True)
    page.get_by_role("button", name=re.compile("\\+30 MIN")).first.click()
    check("forecast strip shows for +30m", page.locator("text=Forecasted Congestion").count() > 0)
    page.get_by_role("button", name=re.compile("NOW")).first.click()

    # Layer toggles
    for name in ["Convoys", "Hazards", "Shelters"]:
        page.get_by_role("button", name=name).first.click()
        page.get_by_role("button", name=name).first.click()
    check("map layer toggles (Convoys/Hazards/Shelters)", True)
    for t in ["Zoom In", "Zoom Out", "Reset Pan/Zoom"]:
        page.get_by_title(t).click()
    check("zoom in / out / reset", True)

    # Evaluate delta + deploy
    page.get_by_text("GMKMC Hospital 100% Saturation").first.click()
    page.get_by_role("button", name=re.compile("Evaluate Delta")).click()
    page.wait_for_selector("text=What-If Delta Analysis", timeout=10000)
    check("Evaluate Delta opens comparison modal", True)
    page.get_by_role("button", name=re.compile("Close & Keep Baseline")).click()
    page.wait_for_timeout(300)
    check("modal Close works", page.locator("text=What-If Delta Analysis").count() == 0)
    page.get_by_role("button", name=re.compile("Evaluate Delta")).click()
    page.wait_for_selector("text=What-If Delta Analysis", timeout=10000)
    page.get_by_role("button", name=re.compile("Deploy Intervention")).click()
    page.wait_for_selector("text=SCENARIO ACTIVE", timeout=5000)
    check("Deploy intervention -> SCENARIO ACTIVE badge", True)
    page.screenshot(path="./scenario_active.png")

    # Apply 2x same scenario: capacity must not compound
    st1 = json.loads(page.evaluate("fetch('http://localhost:8000/twin/shelters').then(r=>r.text())"))
    page.get_by_role("button", name=re.compile("Apply to Live Twin")).click(); page.wait_for_timeout(700)
    st2 = json.loads(page.evaluate("fetch('http://localhost:8000/twin/shelters').then(r=>r.text())"))
    check("re-applying scenario does not compound capacity",
          [s["total_capacity"] for s in st1] == [s["total_capacity"] for s in st2])

    # Clear
    page.get_by_role("button", name=re.compile("Clear Interventions")).click(); page.wait_for_timeout(700)
    check("Clear Interventions removes badge", page.locator("text=SCENARIO ACTIVE").count() == 0)
    st3 = json.loads(page.evaluate("fetch('http://localhost:8000/twin/shelters').then(r=>r.text())"))
    check("Clear restores GMKMC capacity to 1400", next(s for s in st3 if s["id"]=="SHELTER_GMKMC")["total_capacity"] == 1400)

    # Road control list: close then reopen a road (any row beyond the first four)
    row = page.locator("text=Road Control").locator("xpath=../..").locator("div.cursor-pointer").nth(8)
    name = row.inner_text().split("\n")[0]
    row.click(); page.wait_for_timeout(800)
    roads = json.loads(page.evaluate("fetch('http://localhost:8000/twin/roads').then(r=>r.text())"))
    closed = [r["id"] for r in roads if r["is_closed"]]
    check("Road Control closes a road beyond the first four", len(closed) == 2, f"{name}: {closed}")
    page.locator("text=Road Control").locator("xpath=../..").locator("div.cursor-pointer").nth(8).click(); page.wait_for_timeout(800)
    roads = json.loads(page.evaluate("fetch('http://localhost:8000/twin/roads').then(r=>r.text())"))
    check("same row reopens the road", not any(r["is_closed"] for r in roads))
    page.get_by_role("button", name=re.compile("Clear Interventions")).click(); page.wait_for_timeout(500)

    # Canvas click selects a road
    canvas = page.locator("canvas")
    box = canvas.bounding_box()
    selected = False
    for fx in [0.3, 0.4, 0.5, 0.6, 0.7]:
        for fy in [0.3, 0.4, 0.5, 0.6, 0.7]:
            page.mouse.click(box["x"] + box["width"]*fx, box["y"] + box["height"]*fy)
            if page.locator("text=Simulate closure").count() or page.locator("text=Reopen road").count():
                selected = True; break
        if selected: break
    check("clicking a road on the map opens its detail card", selected)
    if selected:
        page.get_by_role("button", name="Simulate closure").click(); page.wait_for_timeout(700)
        check("detail-card 'Simulate closure' closes the road", page.locator("text=Reopen road").count() == 1)
        page.get_by_role("button", name="Reopen road").click(); page.wait_for_timeout(700)
        check("detail-card 'Reopen road' reopens it", page.locator("text=Simulate closure").count() == 1)
        page.get_by_role("button", name="Clear Interventions").click(); page.wait_for_timeout(500)

    # Export
    page.get_by_role("button", name=re.compile("Export Audit")).click()
    page.wait_for_selector("text=Generate Incident Audit Report")
    with page.expect_download(timeout=10000) as d:
        page.get_by_role("button", name=re.compile("Download PDF Audit")).click()
    pdf = d.value; pdf.save_as("./audit.pdf")
    check("Download PDF Audit", pdf.suggested_filename.endswith(".pdf"))
    with page.expect_download(timeout=10000) as d:
        page.get_by_role("button", name=re.compile("Export Raw JSON")).click()
    check("Export Raw JSON", d.value.suggested_filename.endswith(".json"))
    page.locator("button:has(svg.lucide-x)").first.click(); page.wait_for_timeout(300)
    check("export modal closes", page.locator("text=Generate Incident Audit Report").count() == 0)

    # AI Model Hub Modal
    page.get_by_role("button", name=re.compile("AI Hub")).click()
    page.wait_for_selector("text=Enterprise AI & Machine Learning Hub", timeout=5000)
    check("AI Hub button opens AI & Machine Learning Hub", True)
    page.get_by_role("button", name="Close").click(); page.wait_for_timeout(300)
    check("AI Hub modal closes", page.locator("text=Enterprise AI & Machine Learning Hub").count() == 0)

    # Weather & Environmental Simulator Modal
    page.locator("button[title*='modulate rainfall']").click()
    page.wait_for_selector("text=Environmental & Weather Simulator", timeout=5000)
    check("Weather chip opens Environmental Simulator", True)
    page.get_by_role("button", name="Cancel").click(); page.wait_for_timeout(300)
    check("Weather modal closes", page.locator("text=Environmental & Weather Simulator").count() == 0)

    # Analytics Trends Modal
    page.get_by_role("button", name=re.compile("Trends")).click()
    page.wait_for_selector("text=Dynamic Evacuation Analytics & Time-Series Trends", timeout=5000)
    check("Trends button opens Evacuation Analytics modal", True)
    page.get_by_role("button", name="Close Analytics View").click(); page.wait_for_timeout(300)
    check("Analytics trends modal closes", page.locator("text=Dynamic Evacuation Analytics & Time-Series Trends").count() == 0)

    # Reset button
    page.get_by_title("Start Simulation").click(); page.wait_for_timeout(2500)
    page.get_by_title("Reset to Initial Baseline").click(); page.wait_for_timeout(800)
    clock = page.locator("text=/T\\+ [0-9.]+m/").first.inner_text()
    check("Reset returns clock to T+ 0.0m and stops", "0.0m" in clock and page.locator("button[title='Start Simulation']").count() == 1, clock)

    page.screenshot(path="./final.png")
    real_errors = [e for e in errors if "favicon" not in e.lower() and "fonts.g" not in e.lower() and "ERR_" not in e]
    check("no uncaught browser errors", len(real_errors) == 0, "; ".join(real_errors)[:200])
    b.close()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results)-len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
