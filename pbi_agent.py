"""
Power BI AI Agent — Local Mode, powered by Groq (free, no card, no region issues)
Run: python pbi_agent.py
"""

import os
import json
from groq import Groq
from color_engine import ColorEngine
from theme_builder import ThemeBuilder
from pbi_client    import PBIClient

# ── CONFIG — paste your free Groq key here ─────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
# ───────────────────────────────────────────────────────────────────────────────


def main():
    print("\n╔══════════════════════════════════════════════╗")
    print("║     Power BI AI Agent  v4.0                  ║")
    print("║   Powered by Groq — Free, no card needed     ║")
    print("╚══════════════════════════════════════════════╝\n")

    # Quick API test
    try:
        test = Groq(api_key=GROQ_API_KEY)
        test.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        print("Groq API connected\n")
    except Exception as e:
        print(f"Groq API failed: {e}")
        print("\nGet your free key at: https://console.groq.com")
        return

    pbi   = PBIClient()
    color = ColorEngine(GROQ_API_KEY)
    theme = ThemeBuilder()

    # ── Locate .pbix file ──────────────────────────────────────────────────────
    print(" Searching for .pbix files on your computer…")
    found = pbi.find_pbix_files()

    if not found:
        print("\n No .pbix files found in common locations.")
        path = input("Paste the full path to your .pbix file: ").strip().strip('"')
        pbi.set_pbix(path)
    else:
        print(f"\n Found {len(found)} .pbix file(s):\n")
        for i, f in enumerate(found):
            print(f"   [{i+1}] {f}")
        print(f"   [{len(found)+1}] Enter path manually")
        choice = int(input("\nSelect file number: ")) - 1
        if choice == len(found):
            path = input("Paste the full path: ").strip().strip('"')
            pbi.set_pbix(path)
        else:
            pbi.set_pbix(str(found[choice]))

    pages = pbi.list_pages()
    print(f"\n Pages found ({len(pages)}):")
    for p in pages:
        print(f"   • {p['displayName']}")

    print("\n" + "─"*50)
    print("MODES:")
    print("  1. describe  — describe a vibe, AI picks colors")
    print("  2. browse    — choose from curated palettes")
    print("  3. auto      — AI auto-detects best theme per page")
    print("  4. apply     — inject themes into your .pbix file")
    print("  5. export    — save theme JSON files (manual import)")
    print("  6. chat      — ask the AI about your dashboard")
    print("  7. quit")
    print("─"*50)

    last_theme = {}
    groq_client = Groq(api_key=GROQ_API_KEY)

    while True:
        print()
        mode = input("Mode > ").strip().lower()

        if mode in ("1", "describe"):
            page_name = input("Which page? (or 'all'): ").strip()
            vibe      = input("Describe the vibe (e.g. 'dark luxury navy gold'): ").strip()
            targets   = pages if page_name.lower() == "all" else [p for p in pages if p["displayName"].lower() == page_name.lower()]
            for pg in targets:
                print(f"\n🎨 Generating palette for '{pg['displayName']}'…")
                palette = color.from_description(vibe, pg["displayName"])
                last_theme[pg["displayName"]] = palette
                _print_palette(pg["displayName"], palette)

        elif mode in ("2", "browse"):
            page_name = input("Which page? (or 'all'): ").strip()
            targets   = pages if page_name.lower() == "all" else [p for p in pages if p["displayName"].lower() == page_name.lower()]
            for pg in targets:
                options = color.curated_palettes_for_page(pg["displayName"])
                print(f"\n Curated palettes for '{pg['displayName']}':")
                for i, opt in enumerate(options):
                    print(f"   [{i+1}] {opt['name']:20s}  {' '.join(opt['colors'][:4])}")
                pick    = int(input("   Choose palette number: ")) - 1
                palette = color.build_full_palette(options[pick])
                last_theme[pg["displayName"]] = palette
                _print_palette(pg["displayName"], palette)

        elif mode in ("3", "auto"):
            print("\n Auto-detecting themes for all pages…")
            for pg in pages:
                print(f"   Analysing '{pg['displayName']}'…")
                palette = color.auto_detect(pg["displayName"])
                last_theme[pg["displayName"]] = palette
                _print_palette(pg["displayName"], palette)

        elif mode in ("4", "apply"):
            if not last_theme:
                print("  Generate a theme first (modes 1, 2, or 3).")
                continue
            confirm = input(f"\nInject {len(last_theme)} theme(s) into your .pbix? Backup is made first. (yes/no): ").strip().lower()
            if confirm != "yes":
                print("   Cancelled.")
                continue
            for page_name, palette in last_theme.items():
                pbix_theme = theme.build_pbix_theme(page_name, palette)
                success    = pbi.apply_theme("local", pbix_theme)
                if success:
                    print(f" Theme injected for '{page_name}'")
                else:
                    print(f"  Use export mode and import manually instead.")
            print("\n Done! Open your .pbix in Power BI Desktop to see the changes.")

        elif mode in ("5", "export"):
            if not last_theme:
                print("  Generate a theme first (modes 1, 2, or 3).")
                continue
            for page_name, palette in last_theme.items():
                pbix_theme = theme.build_pbix_theme(page_name, palette)
                fname      = f"theme_{page_name.replace(' ','_')}.json"
                with open(fname, "w") as f:
                    json.dump(pbix_theme, f, indent=2)
                print(f"    Saved → {fname}")
            print("\n In Power BI Desktop: View → Themes → Browse for themes → select JSON")

        elif mode in ("6", "chat"):
            print("\n💬 AI Chat (type 'back' to return)\n")
            history = [{
                "role": "system",
                "content": f"""You are a Power BI design AI agent.
Pages: {[p['displayName'] for p in pages]}.
Current themes: {json.dumps(last_theme) if last_theme else 'None yet.'}.
Be concise and actionable."""
            }]
            while True:
                user_input = input("You: ").strip()
                if user_input.lower() == "back":
                    break
                history.append({"role": "user", "content": user_input})
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=history,
                    max_tokens=600,
                )
                reply = response.choices[0].message.content
                print(f"\nAgent: {reply}\n")
                history.append({"role": "assistant", "content": reply})

        elif mode in ("7", "quit", "q"):
            print(" Goodbye!")
            break
        else:
            print("Unknown mode. Type 1–7.")


def _print_palette(page_name, palette):
    print(f"\n    {page_name}")
    print(f"     Background   : {palette.get('background','—')}  |  Canvas: {palette.get('canvas_bg','—')}")
    print(f"     Chart colors : {', '.join(palette.get('chart_colors', []))}")
    print(f"     Table header : {palette.get('table_header','—')}  font: {palette.get('table_header_font','—')}")
    print(f"     Table rows   : base {palette.get('table_row_base','—')}  alt {palette.get('table_row_alt','—')}")
    print(f"     KPI card     : bg {palette.get('kpi_card_bg','—')}  value {palette.get('kpi_value_color','—')}")
    print(f"     Accent       : {palette.get('accent','—')}  |  Font: {palette.get('font_color','—')}")
    print(f"     Vibe         : {palette.get('vibe_summary','—')}")


if __name__ == "__main__":
    main()
