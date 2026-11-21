# Griductive Solver

CSC14003 – Nhập môn Trí tuệ Nhân tạo, Project 2 (HCMUS). Bộ giải **không đoán mò** cho trò chơi suy luận trên lưới Griductive, xây dựng trên logic mệnh đề, mã hoá CNF và bộ giải SAT DPLL tự cài đặt.

Mỗi người trên lưới là `CRIMINAL` (tội phạm) hoặc `INNOCENT` (vô tội) một cách bí mật. Một phán quyết chỉ được chấp nhận nếu nó **được suy ra logic** từ các manh mối đã được tiết lộ; phán quyết đúng sẽ lật một thẻ bài và tiết lộ manh mối mới.

> **Trạng thái:** đang ở giai đoạn lên kế hoạch. Hiện mới có đặc tả và phân chia công việc; cấu trúc mã bên dưới là mục tiêu đã thống nhất, chưa có trên đĩa.

## Tài liệu

- [docs/statement.md](docs/statement.md) – đề bài (file PDF `docs/AI - Project 2.pdf` là bản chính thức)
- [docs/assignment.md](docs/assignment.md) – phân chia nhóm, giao diện module, tiến độ (tiếng Việt)

## Cách hoạt động

1. **Mã hoá** – mỗi ô _i_ là một biến `C_i` (true = tội phạm), đánh số theo hàng (`A1, B1, C1, A2, …` → `1..N²`). Mỗi manh mối được tiết lộ chuyển thành CNF (biến phụ bắt đầu từ `N²+1`).
2. **Phân loại** – với mỗi ô chưa giải, đặt `KB` = các manh mối đã tiết lộ + các phán quyết đã biết:
   - `KB ∧ ¬C_i` UNSAT → `CRIMINAL`
   - `KB ∧ C_i` UNSAT → `INNOCENT`
   - cả hai SAT → `UNKNOWN`; `KB` UNSAT → `INCONSISTENT`
3. **Kiểm tra phán quyết** – `ACCEPTED`, `NOT_PROVABLE` hoặc `CONTRADICTED`. Không bao giờ đoán.
4. **Vòng lặp** – lấy ô bị buộc đầu tiên (theo thứ tự hàng), lật thẻ, cập nhật KB, lặp lại cho đến khi giải xong hoặc bế tắc (các câu đố mơ hồ / mâu thuẫn sẽ dừng một cách an toàn).

Manh mối: `FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, `AT_MOST` trên các vùng `ROW | COL | NEIGHBORS | CELLS`, cùng các phần mở rộng `PARITY` và `COMPARE`.

## Cấu trúc dự kiến

```
main.py  README.md  requirements.txt
griductive/
  clues.py     schema manh mối, vùng, bộ đánh giá ngữ nghĩa
  engine.py    GameEngine (lời giải ẩn, lật thẻ, public_state)
  encoder.py   manh mối -> CNF, build_kb
  dpll.py      bộ giải SAT (+ thống kê decisions/propagations/backtracks/runtime)
  agent.py     LogicAgent (classify, hint, auto_solve, uniqueness_check)
  gui/         giao diện web hoặc tkinter
puzzles/*.json        3x3, 4x4, 5x5, cùng một câu mơ hồ và một câu mâu thuẫn
experiments/run.py    chạy toàn bộ câu đố, ghi ra CSV
tests/
```

Quy tắc: agent chỉ nhìn thấy `public_state` (`{N, revealed_clues, proved}`) và không bao giờ import engine.

## Cách dùng

Điền vào khi `main.py` đã có:

```bash
pip install -r requirements.txt
python main.py                      # mở GUI
python -m pytest                    # chạy test
python experiments/run.py           # chạy thí nghiệm -> CSV
```

## Nhóm

Xem bảng trong [docs/assignment.md](docs/assignment.md) (thành viên, MSSV, % đóng góp).


## Gridwolf web demo

Playable Flask web app: [web/README.md](web/README.md).

```powershell
cd web
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Open http://127.0.0.1:5000. The web demo includes its existing semantic agent for interactive play; it does not implement the planned CNF encoder or DPLL modules. See the web README for the public-state adapter and integration boundary.
