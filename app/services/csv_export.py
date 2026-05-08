import csv
import io
from typing import Iterable

from app.models import Question, Room


def build_csv(room: Room, questions: Iterable[Question]) -> bytes:
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM so Excel opens correctly
    w = csv.writer(buf)
    w.writerow([
        "question_id", "author_name", "text", "state", "starred",
        "upvote_count", "created_at", "room_title", "room_code",
    ])
    for q in questions:
        state_value = q.state.value if hasattr(q.state, "value") else q.state
        w.writerow([
            q.id, q.author_name, q.text, state_value, q.starred,
            q.upvote_count, q.created_at.isoformat(),
            room.title or "", room.code,
        ])
    return buf.getvalue().encode("utf-8")
