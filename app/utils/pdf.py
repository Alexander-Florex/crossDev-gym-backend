from fpdf import FPDF

from app.models.routine import Routine


def generate_routine_pdf(routine: Routine, student_name: str, trainer_name: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, routine.name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Alumno: {student_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Entrenador: {trainer_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 8, f"Creada: {routine.created_at.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT"
    )

    if routine.description:
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 6, routine.description)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    headers = ["#", "Ejercicio", "Series", "Reps", "Peso", "Descanso", "Notas"]
    widths = [8, 45, 18, 18, 18, 22, 61]
    for header, width in zip(headers, widths, strict=True):
        pdf.cell(width, 8, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for index, exercise in enumerate(routine.exercises, start=1):
        pdf.cell(widths[0], 8, str(index), border=1)
        pdf.cell(widths[1], 8, exercise.exercise_name, border=1)
        pdf.cell(widths[2], 8, str(exercise.sets), border=1)
        pdf.cell(widths[3], 8, str(exercise.reps), border=1)
        pdf.cell(widths[4], 8, str(exercise.weight or "-"), border=1)
        pdf.cell(widths[5], 8, str(exercise.rest_seconds or "-"), border=1)
        pdf.cell(widths[6], 8, exercise.notes or "-", border=1)
        pdf.ln()

    return bytes(pdf.output())
