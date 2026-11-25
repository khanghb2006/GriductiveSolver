# Griductive Solver

**CSC14003 · Nhập môn Trí tuệ Nhân tạo · Project 2**

Khoa Công nghệ Thông tin · Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM

**Bản tổng hợp đang cập nhật · 25/11/2026**

Đồ án triển khai một trò chơi suy luận trên lưới và một bộ giải tự động. Mỗi phán quyết phải đúng trong mọi mô hình thỏa các dữ kiện đang công khai. Khi phán quyết được chấp nhận, Game Engine mở thẻ và thêm manh mối mới cho lượt tiếp theo.

## 1. Kế hoạch và phân công

| Thành viên | Công việc chính | Mục báo cáo | Hoàn thành |
| --- | --- | --- | --- |
| Phạm Minh Đạt | Game Engine, schema, bộ đánh giá và puzzle | Mô hình hóa | Chờ xác nhận |
| Nguyễn Phạm Xuân Cương | Giao diện web và video demo | Giao diện, luồng thao tác | Chờ xác nhận |
| Trần Thành Nhân | Bộ mã hóa CNF, kiểm thử chéo và tổng hợp PDF | Phân công, CNF, tài liệu và phụ lục | Chờ xác nhận |
| Huỳnh Nguyên Phát | DPLL và thực nghiệm | DPLL, bảng đo và phân tích | Chờ xác nhận |
| Huỳnh Bảo Khang | Logic Agent và tích hợp chương trình | Hệ quả logic, kiểm tra nghiệm, vòng suy luận | Chờ xác nhận |

1. Thống nhất schema của manh mối, tọa độ ô và định dạng CNF để các phần có thể phát triển song song.
2. Ghép encoder với agent qua `build_kb`. Dùng evaluator độc lập để đối chiếu công thức trên các phép gán nhỏ.
3. Chạy bộ puzzle sau khi ghép DPLL, hoàn thiện bảng đo và chèn video demo cùng thông tin đóng góp đã được nhóm xác nhận.

Cột hoàn thành dùng tỷ lệ do các thành viên xác nhận. Phân công được ghi theo tài liệu của nhóm. [Phân công](https://github.com/khanghb2006/GriductiveSolver/blob/master/docs/assignment.md)

<!-- pagebreak -->

## 2. Mô hình hóa, giao diện và suy luận

Mỗi ô có một biến Boolean `Cᵢ`, nhận True nếu là Criminal và False nếu là Innocent. Biến chính được cấp số theo hàng, từ trái qua phải. Trên bảng 3×3, A1 có biến 1, B1 có biến 2 và A2 có biến 4. Tên và nghề giúp nhận diện nhân vật. Vùng của clue là hàng, cột, tập ô liệt kê hoặc các ô kề theo tám hướng, loại ô trung tâm.

Game Engine giữ lời giải và các clue còn úp. Khi agent cần suy luận, `knowledge()` cung cấp bố cục, các verdict đã biết và clue đã lật. Encoder chuyển hai nhóm dữ kiện sau thành `KBₜ`. Verdict đã biết trở thành mệnh đề đơn vị. Mỗi lần mở thẻ, agent dựng lại KB từ trạng thái công khai mới.

### Giao diện và thao tác

Flask cung cấp trạng thái công khai cho giao diện Gridwolf. Lưới hiển thị tọa độ, tên, nghề, trạng thái đã biết và các clue mở. Chọn một clue làm nổi bật ô được nhắc tới. Người chơi có thể đổi puzzle, chơi lại, xin gợi ý và chạy Auto Solve theo từng bước.

Một phán quyết về ô còn úp có thể được chấp nhận, bị từ chối vì cả hai vai còn khả dĩ (`NOT_PROVABLE`), hoặc bị bác vì vai đối lập đã được chứng minh (`CONTRADICTED`). Game Engine cập nhật thẻ sau khi phán quyết được chấp nhận.

### DPLL và hệ quả logic

Tại mỗi nút tìm kiếm, lan truyền đơn vị gán literal duy nhất còn có thể làm một mệnh đề đúng. Mệnh đề rỗng báo xung đột. Khi cần phân nhánh, bộ giải thử giá trị của một biến chưa gán theo thứ tự cố định và quay lui nếu nhánh thất bại.

Agent kiểm tra SAT của KB trước. Với mỗi ô chưa mở, nếu thêm `¬Cᵢ` làm KB UNSAT thì ô đó là Criminal. Nếu thêm `Cᵢ` làm KB UNSAT thì ô đó là Innocent. Nếu cả hai phép thử đều SAT, ô vẫn Unknown. Vòng tự giải chọn ô suy ra được đầu tiên theo thứ tự hàng, yêu cầu engine mở thẻ và ghi lại bước, clue hỗ trợ, số truy vấn phân loại và clue mới.

Kiểm tra nghiệm duy nhất chạy riêng với toàn bộ clue và verdict mở đầu. Sau khi tìm mô hình thứ nhất, một mệnh đề chặn đảo dấu của từng biến chính trong mô hình. Nếu công thức mới UNSAT, nghiệm trên lưới là duy nhất. Các biến phụ được bỏ qua trong mệnh đề chặn.

<!-- pagebreak -->

## 3. Mã hóa CNF

Một literal dương `i` biểu diễn `Cᵢ`. Literal âm `−i` biểu diễn `¬Cᵢ`. CNF là hội của các mệnh đề, mỗi mệnh đề là tuyển các literal. Các biến phụ bắt đầu từ `N² + 1` và được cấp liên tiếp trong mỗi lần dựng KB.

### 3.1. Clue nhị phân SAME

Giả sử A1 và B1 cùng trạng thái. Đặt `a = C₁` và `b = C₂`. Điều kiện `a ↔ b` tương đương với hai chiều `a → b` và `b → a`. Thay mỗi kéo theo bằng một phép tuyển cho CNF dưới đây.

~~~text
(¬a ∨ b) ∧ (a ∨ ¬b)
DIMACS literals   [[-1, 2], [1, -2]]
~~~

Với DIFFERENT, thay `b` bằng `¬b` để thu được `(¬a ∨ ¬b) ∧ (a ∨ b)`. Với FACT, một mệnh đề đơn vị là đủ. Ví dụ A1 Innocent sinh `[-1]`.

### 3.2. Clue đếm EXACTLY

Đặt `a, b, c` lần lượt là biến của A1, B1, C1. Để đúng một ô là Criminal, kết hợp hai điều kiện.

- **Ít nhất một.** Mệnh đề `(a ∨ b ∨ c)` loại trường hợp cả ba ô đều Innocent.
- **Nhiều nhất một.** Với mỗi cặp, yêu cầu ít nhất một ô Innocent. Ta có `(¬a ∨ ¬b)`, `(¬a ∨ ¬c)` và `(¬b ∨ ¬c)`.

~~~text
EXACTLY(1, row 1)   [[-1, -2], [-1, -3], [-2, -3], [1, 2, 3]]
~~~

Tổng quát với vùng có `m` ô, AT_MOST(k) duyệt các nhóm `k + 1` ô và phủ định toàn bộ literal trong mỗi mệnh đề. AT_LEAST(k) duyệt các nhóm `m − k + 1` ô và dùng literal dương. EXACTLY ghép hai tập mệnh đề. Bộ mã hóa kiểm tra `0 ≤ k ≤ m`, định danh ô và tính duy nhất của ô trong danh sách vùng.

Khi `k = 0`, AT_LEAST sinh công thức đúng và AT_MOST sinh một literal âm cho từng ô. Khi `k = m`, AT_LEAST sinh một literal dương cho từng ô và AT_MOST sinh công thức đúng. Cách mã hóa tổ hợp phù hợp với các vùng nhỏ của bộ puzzle hiện có. Số mệnh đề có thể tăng nhanh khi danh sách tường minh dài và `k` nằm gần giữa.

<!-- pagebreak -->

## 4. Clue mở rộng và kiểm thử chéo

### PARITY

XOR tích lũy của các biến trong vùng bằng True khi số Criminal là lẻ. Mỗi cổng `z = p XOR q` sinh bốn mệnh đề, mỗi mệnh đề loại một tổ hợp sai của ba biến. Ví dụ, `p = q = True` buộc `z = False` qua mệnh đề `(¬p ∨ ¬q ∨ ¬z)`. Cổng đầu lấy hai literal, các cổng tiếp theo lần lượt nhận kết quả trước và biến kế tiếp. Mệnh đề cuối buộc kết quả theo EVEN hoặc ODD. Vùng rỗng có số đếm bằng 0.

### COMPARE

Với mỗi vế, literal ngưỡng `s(i,k)` cho biết trong `i` ô đầu có ít nhất `k` ô mang vai được đếm. Cổng hồi quy được mã hóa hai chiều.

~~~text
s(i,k) ↔ s(i−1,k) ∨ (xᵢ ∧ s(i−1,k−1))
s(i,0) = True                    s(i,k) = False nếu k > i
~~~

Nếu đếm Innocent thì `xᵢ` là literal âm của ô. Khi hai vùng chồng nhau, cả hai vế dùng cùng biến chính của ô chung. EQ ghép tương đương ở mỗi ngưỡng. GT yêu cầu với mọi `k` từ 0 tới độ dài vùng phải, nếu vế phải đạt `k` thì vế trái đạt `k + 1`. LT hoán đổi hai vế. Số cổng tăng theo bình phương độ dài mỗi vùng.

### Tương thích dữ liệu web

Encoder nhận COMPARE dạng hai region với GT, EQ hoặc LT, và dạng hai vùng láng giềng đếm vai chỉ định của nhánh web. Với CONTIGUOUS, mỗi bộ ba có thứ tự trong hàng tạo một mệnh đề cấm việc hai đầu thuộc vai được đếm nhưng ô giữa thuộc vai kia. Vùng thỏa clue có thể chứa một dải ô liền nhau hoặc không có ô nào mang vai đó.

### Đối chiếu với evaluator

Với mỗi clue kiểm thử trên bảng 3×3, test duyệt cả 512 phép gán cho biến chính. Evaluator tính trực tiếp số đếm, quan hệ hoặc tính liên tiếp. SAT nhận các giá trị của biến chính dưới dạng giả định và tự tìm giá trị biến phụ. Hai kết quả phải đồng nhất trong mọi phép gán. Các ca bổ sung kiểm tra dữ liệu sai, trạng thái công khai, biến phụ giữa nhiều clue và một COMPARE dùng danh sách 25 ô.

~~~powershell
python -m pytest -q
~~~

<!-- pagebreak -->

## 5. Kết quả tích hợp sơ bộ

Quy mô CNF được ghi ở thời điểm mở đầu và khi dùng toàn bộ clue của puzzle. Cả hai phép đo đều tính các phán quyết mở đầu. Hai puzzle có hậu tố `-links` dùng COMPARE ngay từ đầu và cần biến phụ.

| Puzzle | Biến chính | Biến phụ | Mệnh đề mở đầu | Mệnh đề toàn bộ | Nghiệm |
| --- | ---: | ---: | ---: | ---: | --- |
| village-3 | 9 | 0 | 5 | 27 | Duy nhất |
| village-4 | 16 | 0 | 10 | 185 | Duy nhất |
| village-5 | 25 | 0 | 6 | 304 | Duy nhất |
| village-5-mist | 25 | 0 | 7 | 218 | Duy nhất |
| village-3-links | 9 | 19 | 75 | 121 | Duy nhất |
| village-4-links | 16 | 40 | 159 | 519 | Duy nhất |

| Puzzle | Kết quả tự giải | Lượt lật | Lần gọi SAT | Thời gian (s) |
| --- | --- | ---: | ---: | ---: |
| village-3 | COMPLETE | 7 | 385 | 0,015 |
| village-4 | COMPLETE | 14 | 1.897 | 0,175 |
| village-5 | COMPLETE | 23 | 6.601 | 2,111 |
| village-5-mist | COMPLETE | 23 | 6.601 | 1,835 |
| village-3-links | COMPLETE | 7 | 385 | 0,112 |
| village-4-links | COMPLETE | 14 | 1.897 | 2,200 |

Kết quả tự giải dùng encoder và solver tạm trong `game/stub_sat.py`. Số lần gọi SAT được đếm qua một hàm bọc quanh solver, bao gồm phân loại, tìm clue hỗ trợ và kiểm lại verdict trong Game Engine. Thời gian là một lượt `auto_solve` đo bằng `perf_counter` trên Windows với Python 3.13.2, sau khi tạo engine. Các test của agent kiểm tra riêng hai tình huống mơ hồ và mâu thuẫn.

~~~powershell
python main.py --cnf-stats
python main.py --check
python main.py --solve village-3
~~~

### Dữ liệu chờ bổ sung cho bản nộp

Các phép đo chính thức của Phát sẽ dùng cùng một bộ puzzle với mọi cấu hình, ghi số quyết định, lần lan truyền, lần quay lui, runtime và mọi ca lỗi hoặc hết thời gian. Bộ hiện tại có hai puzzle cho mỗi kích thước 3×3, 4×4 và 5×5. Bảng thực nghiệm theo phân công cần thêm một puzzle 3×3 và một puzzle 4×4.

<!-- pagebreak -->

## 6. Tài liệu tham khảo

1. Khoa Công nghệ Thông tin, Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM. *CSC14003, Project 2 – Griductive Solver*, mục 2–4. [Đề bài PDF](https://github.com/khanghb2006/GriductiveSolver/blob/master/docs/AI%20-%20Project%202.pdf)
2. Davis, M., Logemann, G. và Loveland, D. (1962). *A machine program for theorem-proving*. Communications of the ACM, 5(7), 394–397. [Bài báo DPLL](https://doi.org/10.1145/368273.368557)
3. Knotwise Games. Hướng dẫn cách chơi và quy tắc suy luận ở trò chơi gốc. [Griductive Strategy](https://knotwise.games/games/griductive/strategy)
4. Nhóm Griductive Solver. Mã nguồn, lược đồ dữ liệu, hướng dẫn chạy và tài liệu phân công. [GitHub](https://github.com/khanghb2006/GriductiveSolver)

## Phụ lục. Sử dụng AI và video

Codex hỗ trợ đọc đề và phân công, soạn encoder, viết kiểm thử đối chiếu và tổng hợp bản PDF. Tính đúng của mã được kiểm bằng evaluator trực tiếp, bộ test và các lệnh chạy puzzle trong mục 5.

Prompt được dùng để bắt đầu phần việc của Nhân.

> giúp tôi hoàn thành đồ án này: [https://github.com/khanghb2006/GriductiveSolver](https://github.com/khanghb2006/GriductiveSolver)<br>
> đọc assignment cũng như statement của project và hoàn thành nhiệm vụ của Nhân.<br>
> tạo nhánh lên rồi push lên, mở PR

Prompt tạo cảnh Gridwolf bằng image_gen được ghi trong tài liệu đi kèm tài nguyên. [ASSET_NOTES.md](https://github.com/khanghb2006/GriductiveSolver/blob/master/static/scenes/ASSET_NOTES.md)

Nhật ký prompt của các phần còn lại và đường dẫn Google Drive của video demo đang chờ thành viên phụ trách gửi để đưa vào bản nộp.
