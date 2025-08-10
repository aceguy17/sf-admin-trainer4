import json
import os
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(APP_DIR, "data", "questions.json")
PROGRESS_PATH = os.path.join(APP_DIR, "data", "progress.json")

app = FastAPI(title="Salesforce Admin Trainer")

app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

def load_questions():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_progress():
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_progress(progress):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/quiz", response_class=HTMLResponse)
def quiz_get(request: Request):
    questions = load_questions()
    idx = int(request.query_params.get("q", "0"))
    if idx >= len(questions):
        return RedirectResponse(url="/results?total={}&correct={}".format(0, 0), status_code=302)

    question = questions[idx]
    total = len(questions)

    return templates.TemplateResponse(
        "quiz.html",
        {
            "request": request,
            "question": question,
            "question_number": idx + 1,
            "total_questions": total,
            "index": idx,
        },
    )

@app.post("/quiz", response_class=HTMLResponse)
def quiz_post(
    request: Request,
    index: int = Form(...),
    selected_option: int = Form(...),
):
    questions = load_questions()
    total = len(questions)

    if index < 0 or index >= total:
        return RedirectResponse(url="/quiz", status_code=302)

    q = questions[index]
    correct_idx = q["answer_index"]
    is_correct = int(selected_option) == int(correct_idx)

    # log daily activity (UTC date)
    progress = load_progress()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    progress[today] = progress.get(today, 0) + 1
    save_progress(progress)

    feedback = "✅ Correct!" if is_correct else "❌ Incorrect."
    correct_answer = q["options"][correct_idx]
    explanation = q.get("explanation", "")

    next_idx = index + 1
    if next_idx >= total:
        return RedirectResponse(url=f"/results?total={total}&correct=-1", status_code=302)

    return templates.TemplateResponse(
        "feedback.html",
        {
            "request": request,
            "feedback": feedback,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "next_index": next_idx,
        },
    )

@app.get("/results", response_class=HTMLResponse)
def results(request: Request, total: int = 0, correct: int = -1):
    total_questions = len(load_questions())
    score = "-" if correct < 0 else f"{round(100*correct/max(total,1))}%"
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "total": total_questions,
            "correct": "—",
            "score": score,
        },
    )

@app.get("/progress", response_class=HTMLResponse)
def progress(request: Request):
    progress = load_progress()
    total_answered = sum(progress.values()) if progress else 0
    sorted_items = sorted(progress.items())  # list of (date, count)
    return templates.TemplateResponse(
        "progress.html",
        {
            "request": request,
            "total_answered": total_answered,
            "progress_items": sorted_items,
        },
    )

@app.get("/download-progress")
def download_progress():
    if not os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, "w") as f:
            f.write("{}")
    return FileResponse(PROGRESS_PATH, filename="progress.json")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
