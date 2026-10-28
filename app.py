import altair as alt
import pandas as pd
import streamlit as st

from backend.pipeline import parse_results, run, saved_runs
from backend.report import contact, out_name, render, write_csv
from backend.tiktok import TIER_LABEL

st.set_page_config(page_title="TikTok KOL Matcher", layout="wide")
st.title("TikTok KOL Matcher (Thailand)")
st.caption("วิเคราะห์แบรนด์จากหน้า Facebook แล้วหา KOL บน TikTok แยกตาม tier พร้อมช่องทางติดต่อ")

with st.sidebar:
    fb = st.text_input("Facebook page URL", "https://www.facebook.com/CPUCore2Duo")
    site = st.text_input("Website (optional)")
    per_tier = st.slider("KOLs per tier", 1, 10, 5)
    go = st.button("Find KOLs", type="primary", disabled=not fb, width="stretch")
    st.divider()
    st.caption("หรือเปิดผลที่เคยรัน (ไม่สแกนใหม่ ไม่เสียเครดิต)")
    files = saved_runs()
    pick = st.selectbox("Saved results", files, format_func=lambda p: p.stem, disabled=not files)
    upload = st.file_uploader("...or upload a results .json", type="json")
    open_file = st.button("Open results", width="stretch", disabled=not (files or upload),
                          help="ถ้าอัปโหลดไฟล์ไว้ จะเปิดไฟล์ที่อัปโหลดก่อน")

if go:
    try:
        with st.spinner("กำลังดึงข้อมูลและวิเคราะห์ (ขั้น TikTok อาจใช้เวลาหลายนาที)..."):
            st.session_state.result = run(fb, site or None, per_tier)
    except Exception as e:
        st.session_state.pop("result", None)
        st.error(f"Failed: {e}")
elif open_file:
    try:
        text = upload.getvalue().decode("utf-8") if upload else pick.read_text(encoding="utf-8")
        st.session_state.result = parse_results(text)
    except (ValueError, UnicodeDecodeError) as e:  # JSONDecodeError is a ValueError
        st.error(f"เปิดไฟล์ไม่ได้: {e}")

if "result" not in st.session_state:
    st.info("ใส่ Facebook URL ของลูกค้าที่แถบด้านซ้าย แล้วกด Find KOLs")
    st.stop()

brand, ranked = st.session_state.result
tiers = [t for t in TIER_LABEL if ranked.get(t)]

st.header(brand["brand"])
st.write(brand["summary"])
cols = st.columns(3)
for col, (label, key) in zip(cols, (("Audience", "audience"), ("Tone", "tone"), ("Content style", "content_style"))):
    col.markdown(f"**{label}**\n\n{brand[key]}")

if not tiers:
    st.warning("ไม่พบ KOL ที่เหมาะสมใน tier ใดเลย")
    st.stop()

df = pd.DataFrame([{**c, "tier": TIER_LABEL[t], "er_pct": round(c["engagement_rate"] * 100, 1)}
                   for t in tiers for c in ranked[t]])
tier_color = alt.Color("tier:N", title="Tier", scale=alt.Scale(domain=list(TIER_LABEL.values())))
tip = ["handle", "tier", "followers", "avg_views", "er_pct", "relevance", "score"]

with st.container(horizontal=True):
    st.metric("KOLs recommended", len(df), border=True)
    st.metric("Total followers", f"{df.followers.sum():,}", border=True)
    st.metric("Avg engagement", f"{df.er_pct.mean():.1f}%", border=True)
    st.metric("Avg relevance", f"{df.relevance.mean():.1f}/10", border=True)

left, right = st.columns(2)
with left, st.container(border=True):
    st.subheader("Reach vs engagement")
    st.caption("ขวา = ผู้ติดตามมาก · บน = engagement สูง · วงใหญ่ = ยอดวิวเฉลี่ยสูง")
    st.altair_chart(
        alt.Chart(df).mark_circle(opacity=0.8).encode(
            x=alt.X("followers:Q", scale=alt.Scale(type="log"), title="Followers (log scale)"),
            y=alt.Y("er_pct:Q", title="Engagement rate (%)"),
            size=alt.Size("avg_views:Q", title="Avg views"),
            color=tier_color, tooltip=tip,
        ).properties(height=380),
        alt=f"Followers versus engagement rate for {len(df)} recommended KOLs, colored by tier",
    )
with right, st.container(border=True):
    st.subheader("Overall ranking")
    st.caption("คะแนนรวม = relevance + engagement + reach")
    st.altair_chart(
        alt.Chart(df).mark_bar().encode(
            x=alt.X("score:Q", title="Score", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("handle:N", sort="-x", title=None),
            color=tier_color, tooltip=tip,
        ).properties(height=max(380, 22 * len(df))),
        alt=f"Score ranking of {len(df)} recommended KOLs, colored by tier",
    )

st.subheader("Recommended KOLs")
for tab, t in zip(st.tabs([TIER_LABEL[t] for t in tiers]), tiers):
    with tab:
        st.caption(brand.get("kol_strategy", {}).get(t, ""))
        st.dataframe(
            [{"KOL": c["url"], "Followers": c["followers"], "Avg views": c["avg_views"],
              "ER %": round(c["engagement_rate"] * 100, 1), "Relevance": c["relevance"],
              "Score": round(c["score"], 2), "Why": c["reason"], "Contact": contact(c)} for c in ranked[t]],
            column_config={"KOL": st.column_config.LinkColumn(display_text=r"tiktok\.com/(@.+)$")},
            hide_index=True,
            alt=f"Recommended {TIER_LABEL[t]} KOLs",
        )
        for c in ranked[t]:
            with st.expander(f"ร่างข้อความทัก @{c['handle']}"):
                st.write(c.get("pitch", ""))
                st.caption(f"ติดต่อ: {contact(c)}  ·  ตรวจก่อนส่งทุกครั้ง")

csv_name, md_name = out_name(brand, "csv"), out_name(brand, "md")
write_csv(ranked, csv_name)
with st.container(horizontal=True):
    st.download_button("Download CSV", open(csv_name, "rb").read(), csv_name, "text/csv")
    st.download_button("Download report (.md)", render(brand, ranked), md_name, "text/markdown")
st.caption("ER = (likes+comments+shares)/views จากวิดีโอที่ค้นเจอ · ไม่มีข้อมูล audience demographics จากข้อมูลสาธารณะ")
