# Project 2 — Griductive Solver

CSC14003 | Nhập môn Trí tuệ Nhân tạo — Khoa Công nghệ Thông tin, Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM
Bài tập nhóm · ~3 tuần · Ngôn ngữ: **Python**

> Bản chuyển sang Markdown của `AI - Project 2.pdf`. File PDF là nguồn chính thức.
> Các ký hiệu toán trong bảng clue (SAME / DIFFERENT) được dựng lại theo ngữ cảnh; hãy đối chiếu với file PDF.

---

## 1. Giới thiệu

Griductive là một trò chơi suy luận trên lưới, trong đó mỗi người đều bí mật là **Criminal** (tội phạm) hoặc **Innocent** (vô tội). Các phát biểu đang hiển thị đều đúng, và người chơi xác định từng người một thông qua các kết luận có thể chứng minh được. Một kết luận đúng sẽ lật thẻ và hé lộ một phát biểu mới.

**Quy tắc cốt lõi: người chơi KHÔNG được đoán mò.** Một kết luận chỉ được chấp nhận khi nó suy ra được một cách logic từ thông tin hiện có.

Mục tiêu: xây dựng một **bộ giải Griductive không đoán mò** sử dụng **logic mệnh đề, mã hóa CNF và bộ giải SAT DPLL**. Bộ giải chỉ suy ra những kết luận được kéo theo một cách logic, lần lượt hé lộ các clue, và phát hiện các trạng thái mơ hồ hoặc mâu thuẫn.

Trang chơi và hướng dẫn cách chơi: xem các liên kết trong file PDF (Hình 1 là ảnh chụp màn hình khi chơi).

---

## 2. Cách chơi

### 2.1 Bảng chơi và các clue

- Một puzzle là lưới **N × N**, thường **N ∈ {3, 4, 5}**.
- Mỗi ô chứa một nhân vật có trạng thái ẩn là **Criminal** hoặc **Innocent**, cùng với một **clue có cấu trúc**.
- Các hàng được đánh số từ trên xuống dưới, các cột được ký hiệu bằng chữ cái từ trái sang phải (`C2` = cột C, hàng 2).
- Các nhân vật được sắp xếp **theo thứ tự bảng chữ cái của tên hiển thị**.
- Một vài thẻ ban đầu được **lật ngửa**; trạng thái và clue của chúng tạo thành tri thức công khai. Tất cả các thẻ còn lại đều úp.
- Mọi clue đã được hé lộ đều **đúng bất kể trạng thái của chủ sở hữu nó** — đây *không* phải là dạng puzzle người nói thật/người nói dối. Tên và nghề nghiệp không mang ý nghĩa logic nào trừ khi một clue nhắc đến chúng.

**Các vùng (region)** được dùng trong clue:

| Vùng | Định nghĩa |
|---|---|
| Hàng (Row) | tất cả các ô có cùng số hàng |
| Cột (Column) | tất cả các ô có cùng chữ cái cột |
| Láng giềng của một ô (Neighbors) | các ô tiếp xúc với nó theo chiều ngang, dọc hoặc chéo, **không bao gồm chính ô đó** (ô bên trong = 8, ô ở biên/góc ít hơn) |
| Danh sách tường minh (Explicit list) | danh sách các định danh ô phân biệt do clue cung cấp |

Các clue được cung cấp ở **định dạng có cấu trúc**; GUI có thể hiển thị bằng ngôn ngữ tự nhiên, nhưng **không yêu cầu xử lý ngôn ngữ tự nhiên (NLP)**.

### 2.2 Vòng lặp suy luận

Tại bước *t*, cơ sở tri thức **KBₜ** chỉ chứa các clue đã hé lộ và các trạng thái đã được chứng minh trước đó.

1. Chọn một nhân vật chưa giải có trạng thái **bị ép buộc về mặt logic** bởi KBₜ. Nếu có nhiều nhân vật như vậy, chọn theo cách xác định (ví dụ: thứ tự ưu tiên hàng).
2. Nộp kết luận `CRIMINAL` hoặc `INNOCENT`. Nếu được kéo theo, hé lộ thẻ và thêm trạng thái cùng clue của nó để tạo thành KBₜ₊₁.
3. Nếu không trạng thái nào được kéo theo, trả về `UNKNOWN`; không đoán mò và không hé lộ thẻ.
4. Một kết luận bị từ chối sẽ giữ nguyên trạng thái trò chơi. Giao diện báo cáo:
   - `NOT_PROVABLE` — không trạng thái nào bị ép buộc;
   - `CONTRADICTED` — trạng thái **đối lập** bị ép buộc.

Một **puzzle hợp lệ có đúng một** phép gán Criminal/Innocent hoàn chỉnh.

---

## 3. Công thức hóa logic

### 3.1 Biến mệnh đề

Với mỗi nhân vật *i* có một biến Boolean chính:

- `Cᵢ = True` nếu *i* là Criminal
- `Cᵢ = False` nếu *i* là Innocent

Ánh xạ biến phải **mang tính xác định**. Các biến phụ có thể được đưa vào bởi một phép mã hóa, nhưng phải được giữ **tách biệt** với biến chính `Cᵢ`.

### 3.2 Ngôn ngữ clue cốt lõi

Sáu mẫu cốt lõi (vùng *R* = hàng, cột, láng giềng của một ô, hoặc danh sách tường minh):

| Loại clue | Ý nghĩa | Nội dung logic |
|---|---|---|
| `FACT` | Một người được nêu tên có trạng thái cho trước | literal đơn `Cᵢ` hoặc `¬Cᵢ` |
| `SAME` | Hai người được nêu tên có cùng trạng thái | `Cᵢ ↔ Cⱼ` |
| `DIFFERENT` | Hai người được nêu tên có trạng thái khác nhau | `Cᵢ ⊕ Cⱼ` |
| `EXACTLY` | Có đúng *k* người trong vùng là Criminal | `Σᵢ∈R Cᵢ = k` |
| `AT_LEAST` | Có ít nhất *k* người trong vùng là Criminal | `Σᵢ∈R Cᵢ ≥ k` |
| `AT_MOST` | Có nhiều nhất *k* người trong vùng là Criminal | `Σᵢ∈R Cᵢ ≤ k` |

Với các clue đếm, `0 ≤ k ≤ |R|`. Từ *NO* có thể được hiển thị dưới dạng `EXACTLY(0, region)`.

**Mở rộng:** mỗi nhóm phải cài đặt **ít nhất hai phần mở rộng khác nhau** ngoài sáu mẫu cốt lõi. Ví dụ: ràng buộc chẵn lẻ, so sánh giữa các số đếm theo vùng, ràng buộc liên thông, clue hợp (compound), hoặc biểu thức vùng nâng cao (giao, láng giềng chung, ô biên, ô góc, các ô nằm giữa hai nhân vật được nêu tên).

### 3.3 Cơ sở tri thức CNF

- **Không viết tay CNF cho từng puzzle kiểm thử.** Mọi clue đang hoạt động phải được chuyển sang CNF **một cách tự động**.
- Các kết luận đã biết là **mệnh đề đơn vị (unit clause)**.
- Cho phép dùng bất kỳ phép mã hóa cardinality đúng đắn nào; báo cáo phải trình bày các ví dụ suy diễn. Một phép mã hóa tổ hợp trực tiếp là chấp nhận được (các vùng nhỏ).
- Phần cài đặt phải **báo cáo số biến chính, số biến phụ và số mệnh đề** cho mỗi puzzle.

### 3.4 Mô hình so với hệ quả logic

Một mô hình thỏa mãn chỉ là một phép gán khả dĩ. Một kết luận chỉ hợp lệ nếu nó đúng trong **mọi** mô hình của KB hiện tại. Với một nhân vật chưa giải *i* tại bước *t*:

```
KBₜ ⊨  Cᵢ  ⇔  KBₜ ∧ ¬Cᵢ  là UNSAT
KBₜ ⊨ ¬Cᵢ  ⇔  KBₜ ∧  Cᵢ  là UNSAT
```

Do đó:

- trả về `CRIMINAL` nếu `KBₜ ∧ ¬Cᵢ` là UNSAT;
- trả về `INNOCENT` nếu `KBₜ ∧ Cᵢ` là UNSAT;
- trả về `UNKNOWN` nếu cả hai công thức đều SAT;
- trả về `INCONSISTENT` nếu bản thân `KBₜ` là UNSAT.

**Ví dụ.** Các nhân vật A, B với `KB = (C_A ∨ C_B) ∧ (¬C_A ∨ C_B)`. Phép gán `C_A=False, C_B=True` thỏa mãn cả hai mệnh đề → KB là SAT. Để quyết định B, giả sử B Innocent: `KB ∧ ¬C_B = C_A ∧ ¬C_A` → UNSAT, nên `KB ⊨ C_B` và B là Criminal. Cả `KB ∧ C_A` và `KB ∧ ¬C_A` đều SAT, nên A vẫn là `UNKNOWN`.

---

## 4. Yêu cầu

- Mã nguồn bằng **Python**.
- Được phép dùng thư viện hỗ trợ (GUI, cấu trúc dữ liệu), nhưng **các thuật toán chính phải do nhóm tự cài đặt**.
- Mã nguồn phải được tổ chức chuyên nghiệp và rõ ràng.

### 4.1 Cài đặt lại trò chơi (10 điểm)

Một phiên bản Griductive cơ bản có thể chơi được với **GUI** (web hoặc desktop). Giao diện phải:

- Hiển thị lưới, tọa độ hàng/cột, tên và nghề nghiệp của nhân vật, các trạng thái đã biết, các clue đã lật ngửa và các thẻ đang úp.
- Cho phép người dùng gọi một nhân vật là `CRIMINAL` hoặc `INNOCENT`.
- Khi một kết luận được chứng minh và đúng: chấp nhận nó, đánh dấu trạng thái một cách trực quan, **lật thẻ** để hé lộ clue của nhân vật đó.
- Từ chối một kết luận không có cơ sở **mà không hé lộ clue ẩn**, phân biệt `NOT_PROVABLE` và `CONTRADICTED`.
- Cho phép chọn một clue đã hé lộ và **làm nổi bật** các nhân vật/ô mà nó tham chiếu hoặc đếm.
- Cung cấp các nút điều khiển **Load, Restart, Hint, Auto Solve**. Hint phải chỉ ra một clue đã hé lộ liên quan và/hoặc một nhân vật có thể được chứng minh kết luận ở bước tiếp theo.

**Kiến trúc — hai vai trò tách biệt:**

- **Game Engine** nắm giữ toàn bộ puzzle, lời giải ẩn và các clue chưa hé lộ.
- **Logic Agent** chỉ nhận **trạng thái tri thức công khai** (các clue đã hé lộ + các kết luận đã chứng minh). Nó **không được** xem các nhãn ẩn hoặc nội dung clue chưa hé lộ.

### 4.2 Biểu diễn logic tự động và mã hóa CNF (10 điểm)

Một bộ mã hóa có thể tái sử dụng, thực hiện:

- tạo ánh xạ xác định giữa nhân vật ↔ biến mệnh đề;
- kiểm tra tính hợp lệ của tham số clue và các vùng được tham chiếu;
- chuyển **tất cả** các mẫu clue sang CNF;
- thêm các kết luận đã biết dưới dạng mệnh đề đơn vị;
- xây dựng `KBₜ = CNF(các clue đã hé lộ) ∪ các mệnh đề đơn vị cho kết luận đã chứng minh` — các trạng thái ẩn và các clue chưa hé lộ **không được** đưa vào;
- báo cáo số biến và số mệnh đề được sinh ra.

Ngoài ra: ít nhất một **bộ đánh giá ngữ nghĩa trực tiếp** cho mỗi mẫu clue bắt buộc — với một phép gán hoàn chỉnh, nó cho biết clue đó đúng hay không **mà không gọi bộ mã hóa CNF**.

### 4.3 Bộ giải SAT DPLL (10 điểm)

Tối thiểu:

1. Lan truyền đơn vị (unit propagation)
2. Phát hiện xung đột
3. Chọn biến một cách xác định
4. Phân nhánh đệ quy và quay lui
5. Trả về SAT cùng một phép gán hoàn chỉnh, hoặc UNSAT
6. Ghi lại **số quyết định (decisions), số lan truyền (propagations), số lần quay lui (backtracks), thời gian chạy**

Loại bỏ literal thuần (pure-literal elimination) và các heuristic nâng cao là tùy chọn. Bộ giải có thể nhận trực tiếp các giả định (assumptions), hoặc giải KBₜ sau khi thêm các mệnh đề đơn vị tạm thời.

### 4.4 Tác tử suy luận logic (20 điểm)

Một tác tử tự động xây dựng trên bộ giải DPLL. Nó phải:

- phân loại mọi nhân vật chưa xác định là `CRIMINAL`, `INNOCENT` hoặc `UNKNOWN`;
- chỉ chọn một kết luận bị ép buộc và **KHÔNG BAO GIỜ đoán mò**;
- yêu cầu clue tương ứng từ GameEngine sau khi một kết luận được chấp nhận;
- cập nhật KB và tiếp tục cho đến khi giải xong hoặc đạt trạng thái kết thúc khác;
- tạo ra **vết suy luận (deduction trace)**: số thứ tự bước, định danh các clue đang hoạt động, các truy vấn SAT, kết luận, clue mới được hé lộ;
- cung cấp một **phép kiểm tra tính duy nhất riêng biệt** cho toàn bộ tập clue.

Hint có thể chỉ ra một nhân vật đang bị ép buộc; nó **không được** đọc lời giải ẩn.

### 4.5 Thực nghiệm (10 điểm)

Đánh giá toàn bộ hệ thống trên nhiều puzzle **3×3** và **4×4** (puzzle **5×5** có thể là trường hợp kiểm tra áp lực). Với mỗi trường hợp, ghi lại:

1. số biến chính và biến phụ
2. số mệnh đề CNF
3. số lần gọi SAT
4. số quyết định, số lan truyền, số lần quay lui
5. số bước suy luận hoặc số đợt hé lộ (reveal waves)
6. thời gian chạy

Dùng **cùng một tập puzzle cho mọi phép so sánh**. **Báo cáo các trường hợp thất bại và quá thời gian (timeout)** thay vì loại bỏ chúng.

### 4.6 Báo cáo (30 điểm)

Một file **PDF** được trình bày tốt, gồm:

- **Lập kế hoạch dự án và phân công nhiệm vụ** — trách nhiệm của từng thành viên, các nhiệm vụ được giao và **phần trăm hoàn thành** của từng thành viên. Ví dụ: điểm nhóm 9.0, sinh viên A đạt 90% → điểm của A = 9.0 × 90% = 8.1. Đánh giá đóng góp một cách công bằng và chính xác.
- **Công thức hóa bài toán** — biến, ngữ nghĩa clue, Cơ sở tri thức, giao thức hé lộ.
- **Mã hóa CNF** — các suy diễn cho ít nhất **một clue nhị phân** và **một clue đếm**.
- **Thuật toán** — DPLL, phân loại kéo theo (entailment), kiểm tra tính duy nhất, vòng lặp suy luận.
- **Thực nghiệm** — bảng hoặc biểu đồ, nhận xét, các trường hợp thất bại, hạn chế.
- **Tài liệu tham khảo và Phụ lục** — toàn bộ tài liệu tham khảo (bài báo, sách, hướng dẫn, repo GitHub…); Phụ lục nêu cách AI sinh tạo (LLM) được sử dụng và các prompt.

### 4.7 Video demo (10 điểm)

Khoảng **5–10 phút**, tải lên **Google Drive** với quyền "bất kỳ ai có liên kết đều có thể xem". Kiểm tra trong cửa sổ ẩn danh/riêng tư. **KHÔNG nộp liên kết YouTube.**

Phải trình diễn:

- **Giao diện đồ họa (5 điểm)** — GUI.
- **Trình bày tính năng (5 điểm)** — chơi thủ công; chạy các bộ giải (chọn một màn, chạy bộ giải, hiển thị lời giải tìm được).

Yêu cầu có lời thuyết minh hoặc phụ đề bằng tiếng Anh hoặc tiếng Việt.

---

## 5. Nộp bài

- Mã nguồn + báo cáo trong một file nén (`.zip` / `.rar`) đặt tên `StudentID1_StudentID2_...`.
- Nếu > 20 MB, tải lên Google Drive và chia sẻ liên kết. **Không được chỉnh sửa sau hạn nộp.**

```
StudentID1_StudentID2_...
├── Source
│   ├── main.py
│   ├── README.md          (cách chạy)
│   ├── requirements.txt   (các thư viện cần cài)
│   └── ...
└── Report.pdf             (kèm URL video demo)
```

---

## 6. Lưu ý

- Bài tập **nhóm**, ~3 tuần.
- Không hạn chế việc dùng công cụ AI, nhưng hãy sử dụng một cách khôn ngoan. Giảng viên thực hành có thể tổ chức **phỏng vấn vấn đáp bổ sung** với các nhóm ngẫu nhiên để đánh giá mức hiểu biết về project.
- Đạo văn, gian lận hoặc vi phạm quy chế → **0 điểm môn học**.

---

## Tổng hợp điểm

| Phần | Điểm |
|---|---|
| 4.1 Game + GUI | 10 |
| 4.2 Mã hóa CNF | 10 |
| 4.3 DPLL | 10 |
| 4.4 Tác tử logic | 20 |
| 4.5 Thực nghiệm | 10 |
| 4.6 Báo cáo | 30 |
| 4.7 Video | 10 |
| **Tổng** | **100** |
