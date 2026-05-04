import os
import random
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


RECIPIENT_EMAILS = ["abdallah.b.b96@gmail.com"]
SECTIONS_TO_PICK = 3
STUDENTS_TO_PICK = 3

# Section labels in English (A-N) — 14 letters max.
SECTION_LETTERS = [
    "A", "B", "C", "D", "E", "F", "G",
    "H", "I", "J", "K", "L", "M", "N",
]
MAX_SECTIONS_PER_GRADE = len(SECTION_LETTERS)


# ---------- PDF font registration (must support Arabic glyphs) ----------
def _register_pdf_fonts():
    regular_candidates = [
        # Linux (Streamlit Cloud is Debian-based, DejaVu is normally pre-installed)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        # macOS
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    for path in regular_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("PDFFont", path))
                regular = "PDFFont"
                break
            except Exception:
                continue
    for path in bold_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("PDFFont-Bold", path))
                bold = "PDFFont-Bold"
                break
            except Exception:
                continue
    return regular, bold


PDF_FONT, PDF_FONT_BOLD = _register_pdf_fonts()


st.set_page_config(
    page_title="أداة التوزيع العشوائي للمدارس",
    page_icon="random",
    layout="centered",
)

st.markdown(
    """
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #f8f9fa; }
    .stApp [data-baseweb="input"] input,
    .stApp [data-baseweb="textarea"] textarea,
    .stApp [data-testid="stNumberInput"] input { text-align: right; }
    .stApp [data-testid="stMarkdownContainer"] code { direction: ltr; display: inline-block; }

    .header-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        margin-bottom: 30px;
        padding: 20px;
        border-radius: 8px;
    }

    .logo-img {
        height: 60px;
        object-fit: contain;
    }

    .stApp button[kind="primary"] {
        background-color: #000000 !important;
        border-color: #000000 !important;
    }

    .stApp button[kind="primary"]:hover {
        background-color: #333333 !important;
        border-color: #333333 !important;
    }

    .section-title {
        color: #000000;
        font-weight: bold;
        margin-top: 20px;
        padding-bottom: 10px;
        border-bottom: 3px solid #000000;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(
        """
        <div class="header-container">
            <img src="https://cdn.prod.website-files.com/6329b3d03a013549434c36d7/63db8291f09c3df767cbb52f_Mindset-Logo.png" class="logo-img" alt="Mindset">
            <img src="https://qrf.org/themes/custom/qrf/logo.svg" class="logo-img" alt="QRF">
        </div>
        """,
        unsafe_allow_html=True,
    )

st.title("أداة التوزيع العشوائي للمدارس")
st.caption("اختيار الشُعب والطلاب عشوائياً لدراسة على مستوى المدرسة.")


def _init_state():
    defaults = {
        "selected_sections": None,
        "student_results": None,
        "snapshot": None,
        "email_status": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset():
    st.session_state.selected_sections = None
    st.session_state.student_results = None
    st.session_state.snapshot = None
    st.session_state.email_status = None


_init_state()


# ---------- 1. School ID ----------
st.markdown('<h3 class="section-title">١. المدرسة</h3>', unsafe_allow_html=True)
school_id = st.text_input("رقم المدرسة", placeholder="مثال: 1234")


# ---------- 2. Grade range ----------
st.markdown('<h3 class="section-title">٢. المرحلة الدراسية</h3>', unsafe_allow_html=True)
grade_choice = st.radio(
    "ما هي المرحلة الدراسية المطلوبة للتوزيع العشوائي؟",
    options=["الصفوف 1-3", "الصفوف 4-6"],
    horizontal=True,
)
grades = [1, 2, 3] if grade_choice == "الصفوف 1-3" else [4, 5, 6]


# ---------- 3. Sections per grade + randomize button ----------
st.markdown('<h3 class="section-title">٣. عدد الشُعب لكل صف</h3>', unsafe_allow_html=True)
st.caption("تُعنوَن الشُعب تلقائياً (أ، ب، ج ... حتى ن).")

sections_per_grade = {}
cols = st.columns(3)
for i, grade in enumerate(grades):
    with cols[i]:
        n = st.number_input(
            f"عدد شُعب الصف {grade}",
            min_value=0, max_value=MAX_SECTIONS_PER_GRADE, value=3, step=1,
            key=f"sec_count_{grade}",
        )
        sections_per_grade[grade] = int(n)
        if int(n) > 0:
            st.caption(f"الشُعب: {'، '.join(SECTION_LETTERS[:int(n)])}")
        else:
            st.caption("لا توجد شُعب لهذا الصف")

all_sections = [
    (grade, label)
    for grade, n in sections_per_grade.items()
    for label in SECTION_LETTERS[:n]
]
total_sections = len(all_sections)
st.info(f"إجمالي عدد الشُعب: **{total_sections}**")

run_sections = st.button(
    "اختيار الشُعب عشوائياً",
    type="primary",
    disabled=not school_id.strip(),
    use_container_width=True,
)

if run_sections:
    if total_sections >= SECTIONS_TO_PICK:
        picked = random.sample(all_sections, SECTIONS_TO_PICK)
    else:
        picked = all_sections[:]
    picked.sort(key=lambda gs: (gs[0], SECTION_LETTERS.index(gs[1])))
    st.session_state.selected_sections = picked
    st.session_state.student_results = None
    st.session_state.email_status = None
    st.session_state.snapshot = {
        "school_id": school_id.strip(),
        "grade_range": grade_choice,
        "sections_per_grade": dict(sections_per_grade),
    }

if st.session_state.selected_sections:
    st.success("الشُعب المختارة:")
    sec_df = pd.DataFrame(
        st.session_state.selected_sections, columns=["الصف", "الشعبة"]
    )
    st.dataframe(sec_df, hide_index=True, use_container_width=True)


# ---------- 4. Students per section + randomize ----------
if st.session_state.selected_sections:
    st.markdown('<h3 class="section-title">٤. عدد الطلاب في كل شعبة مختارة</h3>', unsafe_allow_html=True)
    students_per_section = {}
    cols = st.columns(len(st.session_state.selected_sections))
    for i, (grade, label) in enumerate(st.session_state.selected_sections):
        with cols[i]:
            n = st.number_input(
                f"الصف {grade} - الشعبة {label}",
                min_value=1, value=20, step=1,
                key=f"stu_count_{grade}_{label}",
            )
            students_per_section[(grade, label)] = int(n)

    run_students = st.button(
        "اختيار الطلاب عشوائياً",
        type="primary",
        use_container_width=True,
    )

    if run_students:
        results = []
        for (grade, label), n in students_per_section.items():
            if n < STUDENTS_TO_PICK:
                chosen = list(range(1, n + 1))
            else:
                chosen = sorted(random.sample(range(1, n + 1), STUDENTS_TO_PICK))
            results.append(
                {"Grade": grade, "Section": label, "Students": chosen, "Total": n}
            )
        st.session_state.student_results = results
        st.session_state.email_status = None


# ---------- PDF builder (English headings + Arabic section labels) ----------
def _table_header_style(last_row_emphasis=False):
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), PDF_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if last_row_emphasis:
        style.extend(
            [
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAEAEA")),
                ("FONTNAME", (0, -1), (-1, -1), PDF_FONT_BOLD),
            ]
        )
    return TableStyle(style)


def build_pdf_report(snap, selected_sections, student_results):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="School Randomization Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontName=PDF_FONT_BOLD,
        fontSize=20,
        textColor=colors.HexColor("#1F3864"),
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "H2Style",
        parent=styles["Heading2"],
        fontName=PDF_FONT_BOLD,
        fontSize=13,
        textColor=colors.HexColor("#1F3864"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName=PDF_FONT,
        fontSize=10,
        leading=13,
    )

    grade_range_en = (
        "Grades 1-3" if snap.get("grade_range") == "الصفوف 1-3" else "Grades 4-6"
    )
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    story = []
    story.append(Paragraph("School Randomization Report", title_style))

    # Metadata block
    meta_data = [
        ["Generated", timestamp],
        ["School ID", snap.get("school_id", "—")],
        ["Grade Range", grade_range_en],
        ["Sections selected per school", str(SECTIONS_TO_PICK)],
        ["Students selected per section", str(STUDENTS_TO_PICK)],
    ]
    meta_table = Table(meta_data, colWidths=[6 * cm, 10 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), PDF_FONT_BOLD),
                ("FONTNAME", (1, 0), (1, -1), PDF_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F2F2")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    story.append(meta_table)

    # Sections per grade
    story.append(Paragraph("1. Sections per Grade (entered by user)", h2_style))
    sec_per_grade_data = [["Grade", "Number of Sections", "Section Labels"]]
    sections_per_grade_snap = snap.get("sections_per_grade", {})
    for grade, n in sections_per_grade_snap.items():
        labels = "، ".join(SECTION_LETTERS[:n]) if n > 0 else "—"
        sec_per_grade_data.append([f"Grade {grade}", str(n), labels])
    total = sum(sections_per_grade_snap.values())
    sec_per_grade_data.append(["Total pool", str(total), ""])

    spg_table = Table(sec_per_grade_data, colWidths=[3 * cm, 4 * cm, 9 * cm])
    spg_table.setStyle(_table_header_style(last_row_emphasis=True))
    story.append(spg_table)

    # Selected sections
    story.append(
        Paragraph(
            f"2. Randomly Selected Sections ({len(selected_sections)} of {total})",
            h2_style,
        )
    )
    sel_data = [["#", "Grade", "Section"]]
    for i, (grade, label) in enumerate(selected_sections, 1):
        sel_data.append([str(i), f"Grade {grade}", f"Section {label}"])
    sel_table = Table(sel_data, colWidths=[2 * cm, 5 * cm, 9 * cm])
    sel_table.setStyle(_table_header_style())
    story.append(sel_table)

    # Selected students
    story.append(Paragraph("3. Randomly Selected Students", h2_style))
    stu_data = [
        ["Grade", "Section", "Total Students", "Selected Student #s"]
    ]
    for r in student_results:
        students_str = ", ".join(f"#{s}" for s in r["Students"])
        stu_data.append(
            [
                f"Grade {r['Grade']}",
                f"Section {r['Section']}",
                str(r["Total"]),
                students_str,
            ]
        )
    stu_table = Table(stu_data, colWidths=[3 * cm, 3 * cm, 3.5 * cm, 6.5 * cm])
    stu_table.setStyle(_table_header_style())
    story.append(stu_table)

    # Footer note
    story.append(Spacer(1, 0.6 * cm))
    story.append(
        Paragraph(
            "<i>This report was generated automatically. Selections are made using "
            "Python's <font face='Courier'>random.sample</font> drawn from system entropy.</i>",
            body_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()




# ---------- 5. Results + PDF + email ----------
if st.session_state.student_results:
    st.markdown('<h3 class="section-title">٥. النتائج</h3>', unsafe_allow_html=True)
    snap = st.session_state.snapshot or {}
    st.markdown(
        f"**رقم المدرسة:** {snap.get('school_id', school_id)}  \n"
        f"**المرحلة:** {snap.get('grade_range', grade_choice)}"
    )

    summary_rows = [
        {
            "الصف": r["Grade"],
            "الشعبة": r["Section"],
            "الطلاب المختارون": "، ".join(f"#{s}" for s in r["Students"]),
            "إجمالي الطلاب": r["Total"],
        }
        for r in st.session_state.student_results
    ]
    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

    school_slug = (snap.get("school_id") or "school").replace(" ", "_") or "school"

    pdf_bytes = build_pdf_report(
        snap,
        st.session_state.selected_sections,
        st.session_state.student_results,
    )

    st.divider()
    st.markdown('<h3 class="section-title">التقرير النهائي (PDF)</h3>', unsafe_allow_html=True)
    st.caption("تقرير منسق باللغة الإنجليزية يحتوي على جميع التفاصيل، جاهز للمشاركة.")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.download_button(
            "تحميل التقرير PDF",
            data=pdf_bytes,
            file_name=f"{school_slug}_randomization_report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    with col2:
        st.button("البدء من جديد", on_click=_reset, use_container_width=True)
