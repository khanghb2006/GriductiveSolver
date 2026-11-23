# Griductive Solver

CSC14003 – Nhập môn Trí tuệ Nhân tạo, Project 2 (HCMUS). Bộ giải **không đoán mò** cho trò chơi suy luận trên lưới Griductive, xây dựng trên logic mệnh đề, mã hoá CNF và bộ giải SAT DPLL tự cài đặt.

Mỗi người trên lưới là `CRIMINAL` (tội phạm) hoặc `INNOCENT` (vô tội) một cách bí mật. Một phán quyết chỉ được chấp nhận nếu nó **được suy ra logic** từ các manh mối đã được tiết lộ; phán quyết đúng sẽ lật một thẻ bài và tiết lộ manh mối mới.

> **Bản chính:** Gridwolf trong [`web/`](web/README.md), dùng Flask + HTML/CSS/JavaScript. Đã có GUI, Game Engine và agent demo suy luận từ dữ kiện công khai. CNF encoder, DPLL và LogicAgent chính thức của nhóm còn chờ tích hợp.

## Tài liệu

- [docs/statement.md](docs/statement.md) – đề bài (file PDF `docs/AI - Project 2.pdf` là bản chính thức)
- [docs/assignment.md](docs/assignment.md) – phân chia nhóm, giao diện module, tiến độ (tiếng Việt)

## Thiết kế bộ giải SAT dự kiến

Phần dưới mô tả mục tiêu tích hợp của nhóm. Bản web hiện dùng `ExhaustiveAgent`, chưa dùng CNF/DPLL. Xem [điểm nối thuật toán](web/README.md) để triển khai adapter.

1. **Mã hoá** – mỗi ô _i_ là một biến `C_i` (true = tội phạm), đánh số theo hàng (`A1, B1, C1, A2, …` → `1..N²`). Mỗi manh mối được tiết lộ chuyển thành CNF (biến phụ bắt đầu từ `N²+1`).
2. **Phân loại** – với mỗi ô chưa giải, đặt `KB` = các manh mối đã tiết lộ + các phán quyết đã biết:
   - `KB ∧ ¬C_i` UNSAT → `CRIMINAL`
   - `KB ∧ C_i` UNSAT → `INNOCENT`
   - cả hai SAT → `UNKNOWN`; `KB` UNSAT → `INCONSISTENT`
3. **Kiểm tra phán quyết** – `ACCEPTED`, `NOT_PROVABLE` hoặc `CONTRADICTED`. Không bao giờ đoán.
4. **Vòng lặp** – lấy ô bị buộc đầu tiên (theo thứ tự hàng), lật thẻ, cập nhật KB, lặp lại cho đến khi giải xong hoặc bế tắc (các câu đố mơ hồ / mâu thuẫn sẽ dừng một cách an toàn).

Manh mối: `FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, `AT_MOST` trên các vùng `ROW | COL | NEIGHBORS | CELLS`, cùng các phần mở rộng `PARITY` và `COMPARE`.

## Cấu trúc hiện tại

```
web/
  app.py                 Flask, API và phiên chơi
  requirements.txt       Thư viện chạy ứng dụng
  requirements-dev.txt   Thư viện kiểm thử
  game/
    engine.py            GameEngine, trạng thái ẩn và lật thẻ
    logic.py             Interface agent, evaluator, agent demo
    puzzles.py           Bốn màn 3×3, 4×4, 5×5
  static/                JavaScript, CSS, các view và hình ảnh
  templates/index.html   Trang khởi động
  tests/                 Kiểm thử game và giao diện
docs/                    Đề bài, phân công và ghi chú AI
```

Agent hiện chỉ nhận `GameEngine.knowledge()` gồm `{layout, known, clues}`, không nhận đáp án hoặc clue chưa mở. API mục tiêu trong phân công cần adapter khi tích hợp module của nhóm.

## Cách dùng

Linux/macOS, từ gốc repository:

```bash
cd web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Mở **http://127.0.0.1:5000**. Những lần sau chỉ cần kích hoạt môi trường và chạy `python app.py` trong `web/`. Ứng dụng không cần Node.js hoặc bước build frontend.

Kiểm thử, sau khi kích hoạt môi trường trong `web/`:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Xem [web/README.md](web/README.md) để biết cách chạy trên Windows, luật chơi, danh sách nghề, schema và điểm nối thuật toán.

## Nhóm

Xem bảng trong [docs/assignment.md](docs/assignment.md) (thành viên, MSSV, % đóng góp).
