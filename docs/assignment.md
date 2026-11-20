# Phân công — Griductive Solver (Project 2)

Đề: [statement.md](statement.md) · Thời hạn: ~3 tuần · 5 thành viên, mỗi người 1 mảng chính.

## 0. Nhóm

|     | Họ tên                 | Mảng chính                           |
| --- | ---------------------- | ------------------------------------ |
| A   | Phạm Minh Đạt          | Game Engine + Clue model + Bộ puzzle |
| B   | Nguyễn Phạm Xuân Cương | GUI + Video demo                     |
| C   | Trần Thành Nhân        | CNF Encoder + Tổng hợp Report        |
| D   | Huỳnh Nguyên Phát      | DPLL + Experiments                   |
| E   | Huỳnh Bảo Khang        | Logic Agent + Tích hợp `main.py`     |

---

## 1. Hợp đồng giữa các module

Đây là phần quan trọng nhất: 5 người code song song được là nhờ các interface này.

**Cấu trúc thư mục** (khớp yêu cầu nộp bài):

```
Source/
├── main.py  README.md  requirements.txt
├── griductive/
│   ├── clues.py     # Đạt: schema clue, region, evaluator
│   ├── engine.py    # Đạt: GameEngine
│   ├── encoder.py   # Nhân: CNF
│   ├── dpll.py      # Phát: SAT solver
│   ├── agent.py     # Khang: LogicAgent
│   └── gui/         # Cương
├── puzzles/*.json   # Đạt
├── experiments/run.py   # Phát
└── tests/
```

**Clue (JSON, dict trong Python)** — Đạt định nghĩa, mọi người dùng:

```json
{"id":"c7","type":"FACT","cell":"B2","status":"CRIMINAL"}
{"id":"c8","type":"SAME","cells":["A1","C3"]}                    // DIFFERENT tương tự
{"id":"c9","type":"EXACTLY","region":{"kind":"ROW","row":2},"k":2}   // AT_LEAST, AT_MOST tương tự
 region.kind ∈ ROW(row) | COL(col) | NEIGHBORS(cell) | CELLS(cells[])
```

**2 extension chọn sẵn**: `PARITY` (`region`, `parity: EVEN|ODD`) và `COMPARE` (`left`, `op: GT|EQ|LT`, `right`, hai vế là region).

**Biến & CNF:** biến chính `C_i` = số `1..N²`, đánh theo thứ tự hàng trước (row-major: A1, B1, C1, A2, …). Biến phụ bắt đầu từ `N²+1`. CNF = `list[list[int]]`, literal có dấu kiểu DIMACS.

**API:**

| Module         | Hàm                                                                                                                    | Trả về                                                                                      |
| -------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Engine (Đạt)   | `load(path)`, `restart()`, `public_state()`, `reveal(cell, status)`                                                    | `public_state` = `{N, revealed_clues, proved}` — **không chứa** nghiệm ẩn hay clue chưa lật |
| Encoder (Nhân) | `build_kb(public_state)` → `KB(clauses, n_primary, n_aux)`; `encode_clue(clue, N)`                                     |                                                                                             |
| DPLL (Phát)    | `solve(clauses, n_vars, assumptions=())`                                                                               | `SolveResult(sat, model, stats{decisions, propagations, backtracks, runtime})`              |
| Agent (Khang)  | `classify(cell)`, `check_verdict(cell, verdict)`, `hint()`, `step()`, `auto_solve()`, `uniqueness_check(all_clues, N)` | `CRIMINAL/INNOCENT/UNKNOWN/INCONSISTENT`; `ACCEPTED/NOT_PROVABLE/CONTRADICTED`; trace       |

**Luồng 1 verdict** (GUI/Agent gọi, Engine không tự suy luận): `Agent.check_verdict` → nếu `ACCEPTED` thì `Engine.reveal` → Engine **assert** verdict khớp nghiệm ẩn (bắt puzzle sai) → lật thẻ, trả clue mới.

**Quy tắc cứng:** Agent chỉ nhận `public_state`. Không import `engine` trong `agent.py`.

---

## 2. Năm đầu việc

### Đạt — Game Engine, Clue model, Bộ puzzle &nbsp;_(4.1 phần backend, 4.2 evaluator)_

**Làm:**

1. `clues.py`: schema clue, resolve region (ROW/COL/NEIGHBORS/CELLS, **loại ô chính nó** khỏi neighbors), validate tham số (`0 ≤ k ≤ |R|`, ô tồn tại, ô không trùng).
2. **Semantic evaluator** cho 6 clue core + 2 extension: `evaluate(clue, assignment) -> bool`, **không gọi encoder**.
3. `engine.py`: giữ nghiệm ẩn + clue chưa lật; sắp xếp nhân vật theo **tên alphabet** để ra vị trí ô; load/restart; reveal; tách `public_state`.
4. **Bộ puzzle** `puzzles/*.json`: ≥3 bài 3×3, ≥3 bài 4×4, ≥1 bài 5×5 (stress). Thêm 1 bài **mơ hồ** (nhiều nghiệm) và 1 bài **mâu thuẫn** để thử `UNKNOWN`/`INCONSISTENT`. Mỗi bài có tên + nghề cho từng nhân vật.

**Xong khi:** evaluator có test cho từng loại clue; mọi puzzle có đúng 1 nghiệm. Ban đầu kiểm bằng brute-force (3×3, 4×4 dùng được); 5×5 dùng `uniqueness_check` của Khang khi Khang xong.

**Phụ thuộc:** không ai. **Cần giao sớm** (ngày 3–4): schema + vài puzzle mẫu cho cả nhóm.

**Report:** _Problem formulation_ (biến, ngữ nghĩa clue, KB, reveal protocol).

### Cương — GUI + Video &nbsp;_(4.1 phần giao diện, 4.7)_

**Làm:**

1. Web React(Frontend) + Flask (Backend)
2. Hiển thị: lưới, toạ độ hàng/cột, tên + nghề, trạng thái đã biết, clue của thẻ ngửa, thẻ úp.
3. Nút gọi `CRIMINAL` / `INNOCENT`; đúng → đánh dấu + **lật thẻ**; sai → báo `NOT_PROVABLE` hoặc `CONTRADICTED` (phân biệt rõ), **không lộ clue ẩn**.
4. Chọn 1 clue đã lật → **highlight** các ô được nhắc/đếm.
5. Nút **Load, Restart, Hint, Auto Solve** (Auto Solve chạy từng bước để nhìn thấy được, không nhảy một phát).
6. **Video 5–10 phút**, có thuyết minh hoặc phụ đề; chơi tay + chạy solver trên 1 stage; up Google Drive "anyone with link", thử bằng cửa sổ ẩn danh; **không dùng YouTube**.

**Xong khi:** chạy được ngay cả khi Agent chỉ là stub trả `NOT_PROVABLE` (dựng GUI trên stub, không phải đợi Khang).

**Phụ thuộc:** API Engine (Đạt) và Agent (Khang) — dùng stub trước, ghép thật ở tuần 2.

**Report:** mô tả giao diện + kiến trúc Engine/Agent; chèn link video.

### Nhân — CNF Encoder + Tổng hợp Report &nbsp;_(4.2, ghép 4.6)_

**Làm:**

1. `encoder.py`: ánh xạ ô ↔ biến (deterministic), validate, đổi **mọi** clue sang CNF tự động (6 core + 2 extension), thêm verdict đã biết thành unit clause, `build_kb`.
2. Mã hoá đếm (`EXACTLY/AT_LEAST/AT_MOST`) bằng cách tổ hợp trực tiếp (vùng nhỏ nên chấp nhận được). `PARITY`/`COMPARE` có thể cần biến phụ — giữ biến phụ **tách riêng** khỏi `C_i`.
3. Báo số biến chính / biến phụ / mệnh đề của mỗi puzzle.
4. **Test chéo với Đạt:** với mỗi clue và **mọi** phép gán của vùng nhỏ, `CNF thoả ⇔ evaluator đúng`. Test này bắt hầu hết lỗi encoder.
5. **Tổng hợp Report PDF:** gom các phần của từng người, thống nhất format, viết mục _Planning & Task Distribution_ (bảng ở trên + %), _References_, _Appendix_ (cách dùng AI/LLM + prompt đã dùng — nhắc mọi người lưu prompt từ đầu).

**Xong khi:** test chéo qua cho 8 loại clue; có thể in số biến/mệnh đề cho 1 puzzle.

**Phụ thuộc:** schema + evaluator (Đạt). Bắt đầu viết trên schema, test chéo khi Đạt giao evaluator.

**Report:** _CNF encoding_ — suy dẫn tay ≥1 clue nhị phân (vd `SAME`) và ≥1 clue đếm (vd `EXACTLY`).

### Phát — DPLL + Experiments &nbsp;_(4.3, 4.5)_

**Làm:**

1. `dpll.py`: unit propagation, phát hiện xung đột, chọn biến **deterministic** (vd biến nhỏ nhất chưa gán), phân nhánh đệ quy + quay lui, trả `SAT` + model đầy đủ hoặc `UNSAT`; hỗ trợ `assumptions`; ghi **decisions / propagations / backtracks / runtime**.
2. Test: so với brute-force trên CNF ngẫu nhiên nhỏ; ví dụ trong đề (`KB ∧ ¬C_B` UNSAT).
3. `experiments/run.py`: chạy toàn bộ bộ puzzle (cùng một bộ cho mọi so sánh), ghi mỗi bài: biến chính/phụ, số mệnh đề, số SAT call, decisions/propagations/backtracks, số bước (hoặc wave), runtime. **Ghi cả bài lỗi/timeout, không bỏ.** Xuất CSV + bảng/biểu đồ.
4. _(Tuỳ chọn, nên có 1)_ so sánh DPLL có/không pure-literal, hoặc 2 cách chọn biến — để mục Experiments có "so sánh" thật.

**Xong khi:** DPLL qua test random; `run.py` ra được bảng cho ≥3 bài 3×3 và ≥3 bài 4×4.

**Phụ thuộc:** DPLL độc lập (làm trước, giao ở cuối tuần 1 vì Khang cần). Experiments cần Encoder + Agent → tuần 2–3.

**Report:** _Algorithms — DPLL_, và toàn bộ _Experiments_ (bảng, quan sát, ca lỗi, hạn chế).

### Khang — Logic Agent + Tích hợp &nbsp;_(4.4, `main.py`)_

**Làm:**

1. `agent.py`: nhận **chỉ** `public_state`; dựng KB bằng Encoder; `classify` mỗi nhân vật chưa giải: `KB ∧ ¬C_i` UNSAT → `CRIMINAL`; `KB ∧ C_i` UNSAT → `INNOCENT`; cả hai SAT → `UNKNOWN`; bản thân KB UNSAT → `INCONSISTENT`.
2. `check_verdict` → `ACCEPTED / NOT_PROVABLE / CONTRADICTED`. **Không đoán.**
3. Vòng lặp: chọn ô forced đầu tiên theo row-major → xin Engine lật → cập nhật KB → lặp tới khi xong hoặc dừng (không còn ô forced / mâu thuẫn). Dừng đúng với puzzle mơ hồ.
4. **Deduction trace:** số bước, id clue đang dùng, các SAT query, verdict, clue mới lật.
5. `uniqueness_check(all_clues, N)` **riêng**: tìm 1 nghiệm → thêm blocking clause → UNSAT thì duy nhất. Dùng cho Đạt kiểm puzzle.
6. `hint()` (một ô forced + clue liên quan, **không đọc nghiệm ẩn**) và `auto_solve()`.
7. `main.py` + `README.md` + `requirements.txt`: ghép tất cả, chạy được bằng một lệnh.

**Xong khi:** giải trọn bộ puzzle hợp lệ mà không lần nào đoán; bài mơ hồ/mâu thuẫn dừng đúng trạng thái.

**Phụ thuộc:** Encoder (Nhân) + DPLL (Phát) + Engine (Đạt). Tuần 1: viết trên stub encoder/solver (brute-force) để không bị chặn.

**Report:** _Algorithms_ — entailment classification, uniqueness checking, deduction loop.

---

## 4. Report — ai viết phần nào (30 điểm)

| Mục báo cáo                                             | Người viết                       | Người ghép |
| ------------------------------------------------------- | -------------------------------- | ---------- |
| Planning & Task Distribution, References, Appendix (AI) | Nhân (mọi người gửi % và prompt) | Nhân       |
| Problem formulation                                     | Đạt                              | Nhân       |
| GUI + kiến trúc Engine/Agent                            | Cương                            | Nhân       |
| CNF encoding (suy dẫn)                                  | Nhân                             | Nhân       |
| Algorithms: DPLL                                        | Phát                             | Nhân       |
| Algorithms: entailment, uniqueness, deduction loop      | Khang                            | Nhân       |
| Experiments                                             | Phát                             | Nhân       |

## 5. Quy ước

- Mỗi module có ≥1 test chạy được (`python -m pytest` hoặc `assert` trong `__main__`) — không cần framework nặng.
- Mỗi người lưu **prompt đã dùng với AI** ngay từ đầu để Nhân đưa vào Appendix. Thầy có thể phỏng vấn miệng: **ai cũng phải giải thích được phần của mình và đại ý của phần liền kề.**
- Đổi API/schema → báo cả nhóm trước khi merge.
- Mỗi người commit riêng file của mình để dễ chứng minh % đóng góp.
