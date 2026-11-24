# Gridwolf — bàn giao phạm vi 4.1

Web game Ma Sói suy luận trên lưới, Python/Flask + HTML/CSS/JavaScript thuần. Bản gốc bàn giao game/GUI theo mục 4.1; hiện đã thêm hai clue thử nghiệm COMPARE và CONTIGUOUS cùng hai màn mới. Agent demo hỗ trợ cả hai; chưa có CNF encoder/DPLL chính thức hoặc benchmark của nhóm.

## Chạy web

PowerShell, tại thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Mở **http://127.0.0.1:5000**. Nếu `.venv` đã cài, chỉ cần lệnh cuối. Ctrl+C để dừng. Khi sửa file Python/dữ liệu màn, cần khởi động lại server. Khi chỉ sửa UI, Ctrl+F5 là đủ.

Mỗi cookie phiên trỏ tới một ván ở RAM server; không có database hay lưu ván qua lần restart tiến trình. Điều hướng Trang chủ → Chọn màn → Chơi không tự reset ván. Tiếp tục chỉ hiện khi trạng thái server có lịch sử và ván chưa hoàn tất. Chỉ Load/Vào làng hoặc Restart/Chơi lại mới đặt lại ván.

## File chính và ranh giới dữ liệu

| File | Trách nhiệm |
| --- | --- |
| `app.py` | Flask/API, phiên chơi, `create_app(agent_factory=...)` để đăng ký implementation của nhóm. |
| `game/engine.py` | `GameEngine`: puzzle đầy đủ, vai bí mật, clue úp; Load, Restart, kiểm verdict và lật thẻ. |
| `game/puzzles.py` | Sáu hồ sơ cố định, tên/nghề, nhãn, một clue cho mỗi người, thẻ mở sẵn; `DEMO_PROOFS` chỉ dùng để kiểm dữ liệu/walkthrough bốn màn gốc. |
| `game/logic.py` | Interface `LogicAgent`, `Inference`, semantic evaluator và implementation demo **đã có trước** `ExhaustiveAgent`. Được giữ và dùng lại, không viết lại thuật toán trong đợt 4.1 này. |
| `static/views.html`, `static/app.js`, `static/style.css` | Routing hash, render, tương tác, spotlight và responsive. Không chứa đáp án hay clue úp. |
| `static/scenes/gridwolf-village-night.webp` | Cảnh Gridwolf riêng, không lấy asset/nhân vật/logo của Agrou. |
| `tests/test_authored_cases.py` | Dùng agent hiện có để kiểm hai clue cần thiết và không có shortcut từ clue đơn lẻ. |

`GameEngine.knowledge()` trả **bản sao** chỉ gồm `{layout, known, clues}` cho agent. `GameEngine.view()` trả DTO cho frontend gồm layout công khai, known, clue đã mở (cấu trúc + text + cells đã giải vùng), tiến độ, completed và history. Không trả `solution`, `initial` hay clue của người còn úp. Tên và nghề không tự mang ý nghĩa logic.

Mọi clue đã mở đều đúng, kể cả Lời trăn trối của Sói. CRIMINAL hiển thị là Sói; INNOCENT là Dân làng. Highlight bạc biểu thị **được clue nhắc tới**, không biểu thị vai. Vai vẫn có nhãn riêng; ô chọn để phán có viền vàng riêng.

## Điểm nối cho thành viên thuật toán

Hiện cả Verdict, Hint và Auto Solve **đều đã nối thật** tới implementation demo `ExhaustiveAgent` có sẵn. Không dùng đáp án bí mật để thay chứng minh. Không có fixture hoặc đáp án hard-code trong runtime. Phần còn chờ nhóm là adapter CNF/DPLL/thuật toán chính thức, không phải nút giao diện còn rỗng.

### Interface phải giữ

Trong `game/logic.py`:

```python
class LogicAgent(Protocol):
    def classify(self, public_state: dict) -> Inference: ...

@dataclass
class Inference:
    statuses: dict
    model_count: int
```

`statuses` chứa mọi ô chưa mở, giá trị CRIMINAL / INNOCENT / UNKNOWN. Chỉ được trả nhãn khi nó đúng trong **mọi mô hình** của dữ kiện công khai; một mô hình SAT đơn lẻ không đủ để kết tội/minh oan. `model_count=0` khi mâu thuẫn; giá trị dương khi SAT. Adapter SAT có thể trả `1` làm cờ SAT nếu không đếm mô hình, nhưng vẫn phải kiểm hệ quả cho từng ô. Khi mâu thuẫn, trả `Inference({}, 0)`.

### Ba hook dùng cùng adapter

| Hook chính xác | Input | Output / hành vi |
| --- | --- | --- |
| `game/engine.py:GameEngine.verdict(cell, status)` | ID và enum từ UI; engine lấy `knowledge()` rồi gọi `agent.classify(public_state)` | ACCEPTED chỉ khi forced và khớp dữ liệu màn; sau đó cập nhật known, history và mở clue. UNKNOWN → NOT_PROVABLE; nhãn ngược forced → CONTRADICTED. |
| `game/engine.py:GameEngine.hint()` | `knowledge()` tại lượt hiện tại | Dùng `agent.classify()` và `game/logic.py:proof_support()` để chọn clue thực sự hỗ trợ một suy luận; ưu tiên nhóm đếm chồng nhau. Lần đầu gợi cách đọc; lần sau trả `clue_ids` đã mở. Không trả ô đích hoặc verdict cho UI. |
| `game/engine.py:GameEngine.auto_step()` | `knowledge()` tại lượt hiện tại | Chọn ô forced theo thứ tự hàng/cột, gọi lại `verdict()`; clue mới chỉ mở qua engine. Mỗi lần gọi chỉ thực hiện một bước. Frontend chờ khoảng một giây rồi gọi tiếp. |

**Đăng ký:** `app.py:create_app(agent_factory=None)` nhận callable tạo một instance adapter cho mỗi ván/phiên mới. Mặc định `None` giữ implementation demo hiện có. Khi module của nhóm sẵn sàng, trong runner của nhóm:

```python
from app import create_app
from team_solver.adapter import TeamLogicAgent  # module do nhóm cung cấp

server = create_app(agent_factory=TeamLogicAgent)
server.run(host='127.0.0.1', port=5000, debug=False)
```

Không cần thay route hoặc frontend. Để thử riêng engine: `GameEngine('village-3', agent=TeamLogicAgent())`. Không truyền puzzle đầy đủ, solution hoặc kho clue úp vào adapter. Test `test_team_agent_factory_receives_only_public_input_for_all_hooks` kiểm cả ba đường đi; stub UNKNOWN trong test chỉ là fixture kiểm wiring, không được đăng ký trong app thật.

### Ví dụ input công khai ban đầu của tutorial

```json
{
  "layout": [
    {"id":"A1","row":1,"column":1,"name":"An","profession":"Nông dân"},
    {"id":"B1","row":1,"column":2,"name":"Bách","profession":"Thợ may"},
    {"id":"C1","row":1,"column":3,"name":"Chi","profession":"Thợ đóng giày"},
    {"id":"A2","row":2,"column":1,"name":"Đào","profession":"Ngư dân"},
    {"id":"B2","row":2,"column":2,"name":"Giang","profession":"Thợ dệt"},
    {"id":"C2","row":2,"column":3,"name":"Hà","profession":"Thợ rèn"},
    {"id":"A3","row":3,"column":1,"name":"Khôi","profession":"Thợ mộc"},
    {"id":"B3","row":3,"column":2,"name":"Lan","profession":"Thợ làm nến"},
    {"id":"C3","row":3,"column":3,"name":"Minh","profession":"Thợ xây"}
  ],
  "known": {"A1":"INNOCENT","A2":"CRIMINAL"},
  "clues": [
    {"id":"clue-A1","owner":"A1","type":"FACT","cells":["C1"],"status":"INNOCENT"},
    {"id":"clue-A2","owner":"A2","type":"EXACTLY","k":1,"region":{"kind":"LIST","cells":["B1","B2"]}}
  ]
}
```

Output tương ứng của implementation demo:

```python
Inference(statuses={
    'B1':'UNKNOWN', 'C1':'INNOCENT', 'B2':'UNKNOWN', 'C2':'UNKNOWN',
    'A3':'UNKNOWN', 'B3':'UNKNOWN', 'C3':'UNKNOWN'
}, model_count=32)
```

Ví dụ output từng hook trên trạng thái này:

- Verdict `C1 / INNOCENT`: `{"code":"ACCEPTED","message":"C1: phán quyết được chứng minh."}`; response HTTP có thêm `state` với 3 thẻ mở và clue C1.
- Verdict `B1 / CRIMINAL`: NOT_PROVABLE dù B1 trùng nhãn bí mật. Verdict `C1 / CRIMINAL`: CONTRADICTED. Cả hai không đổi state và không trả clue úp.
- Hint lần đầu: `{"code":"HINT","clue_ids":[],"level":1,"message":"..."}`. Lần hai trên cùng lượt: `clue_ids=["clue-A1"]`, không có target/status. Ở bước ghép sau C1/C2, hai ID là `clue-A2`, `clue-C2`.
- Auto Solve bước đầu: ACCEPTED, `state.history[-1] = {"step":1,"cell":"C1","status":"INNOCENT"}`; clue C1 được mở. Bước tiếp theo suy luận lại từ state mới, không lấy sẵn danh sách đáp án.

### API và mã trạng thái

GET `/api/puzzles`, GET `/api/state`. POST nhận JSON:

| Endpoint POST | JSON body |
| --- | --- |
| `/api/load` | `{"puzzle_id":"village-5"}` |
| `/api/verdict` | `{"cell":"C1","status":"INNOCENT"}` |
| `/api/restart`, `/api/hint`, `/api/auto-step` | `{}` |

Response thao tác có `code`, `message`, `state`; Hint thêm `level`, `clue_ids` khi có gợi ý. API giữ nguyên mã:

| Code | Ý nghĩa |
| --- | --- |
| ACCEPTED | Verdict được chứng minh và đúng, lật thẻ. |
| NOT_PROVABLE | Cả hai vai còn khả thi; không lật. |
| CONTRADICTED | Bằng chứng bắt buộc vai ngược lại; không lật. |
| DATA_ERROR | Dữ kiện công khai mâu thuẫn hoặc lệch dữ liệu màn; giữ bàn. |
| ALREADY_REVEALED | Ô đã mở, không thêm bước. |
| INVALID_REQUEST | Input/route không hợp lệ. |
| LOADED / RESTARTED | Đã đặt lại đúng các thẻ mở sẵn. |
| HINT / NO_HINT | Gợi phương pháp/clue, hoặc không còn suy luận mới. |
| STUCK / COMPLETE | Auto Solve hết nước chứng minh được / đã hoàn tất. |

Các kết quả nghiệp vụ trả HTTP 200 với code. JSON/type sai hoặc ID màn sai trả 400, route action không tồn tại trả 404; request cross-site bị chặn bằng 403. CONNECTION_ERROR chỉ là thông báo lỗi kết nối phía UI, không phải nhãn suy luận của backend.

## Dữ liệu màn và cách thêm hồ sơ

Một puzzle giữ các trường hiện có: `id`, `title`, `size`, `layout`, `solution`, `clues`, `initial`. `layout` theo thứ tự hàng rồi cột; tọa độ A–E là cột, 1–5 là hàng. `solution` ánh xạ ID sang bool. `clues` ánh xạ chủ thẻ sang một clue; thêm `id="clue-<owner>"` và `owner`. `initial` chứa ID những thẻ mở đầu.

Hỗ trợ sáu template gốc FACT, SAME, DIFFERENT, EXACTLY, AT_LEAST, AT_MOST và hai extension COMPARE, CONTIGUOUS. Vùng gốc: LIST, ROW, COLUMN (A=1), NEIGHBORS (có đường chéo, không có tâm). `referenced_cells()` giải vùng; frontend lấy trực tiếp `cells` từ DTO công khai, không regex từ lời văn. Evaluator trực tiếp và agent demo đều xử lý được hai extension.

Để thêm màn: tạo một hàm dữ liệu với đủ `size²` nhân vật/clue; đưa kết quả vào `PUZZLES`; thêm kiểm tra cho bước ghép dự kiến; chạy test. Chọn màn tự lấy danh sách từ API. Ba thẻ kích thước 3×3, 4×4, 5×5; mỗi thẻ hiện có hai hồ sơ, chọn bằng nút “Hồ sơ khác”. Không sinh puzzle ngẫu nhiên khi chơi.

### Hai clue thử nghiệm

`COMPARE` so sánh bằng nhau, mỗi vế chọn một tâm và vai được đếm:

```json
{"type":"COMPARE","left":{"cell":"B3","status":"INNOCENT"},"right":{"cell":"C3","status":"CRIMINAL"}}
```

Ví dụ trên: số Dân làng quanh B3 bằng số Sói quanh C3. Mỗi vùng gồm ngang/dọc/chéo, loại chính tâm của vùng đó. Hai vùng có thể chồng nhau và đếm độc lập. Highlight là hợp hai vùng, không tự thêm tâm; một tâm vẫn được highlight nếu thuộc vùng kề của tâm còn lại. Chỉ hỗ trợ quan hệ bằng nhau trong đợt này.

`CONTIGUOUS` yêu cầu tất cả người mang vai chỉ định trên một hàng tạo thành một đoạn liền:

```json
{"type":"CONTIGUOUS","region":{"kind":"ROW","row":2},"status":"CRIMINAL"}
```

Ví dụ: các Sói trên hàng 2 nằm liền nhau, không có Dân làng chen giữa; không nối vòng từ cột cuối về cột đầu. Hàng có 0 hoặc 1 người thuộc vai được đếm cũng thỏa. Chưa mở rộng sang cột. Highlight toàn bộ hàng vì mọi ô trên hàng tham gia ràng buộc.

| Hồ sơ mới | ID | Mở sẵn | Bước đầu cần cả hai extension |
| --- | --- | --- | --- |
| Dấu chân ven hồ · 3×3 | `village-3-links` | A1, A2 | B2 là Sói |
| Dãy nhà im tiếng · 4×4 | `village-4-links` | A1, A2 | C3 là Dân làng |

Cả hai màn có đúng một nghiệm khi tính toàn bộ clue và trạng thái mở sẵn. `tests/test_authored_cases.py` kiểm bằng duyệt toàn bộ phép gán độc lập (128 trường hợp cho 3×3, 16.384 trường hợp cho 4×4), kiểm tra tách từng clue ở bước đầu; `test_game.py` kiểm evaluator và API, `test_gridwolf.py` đối chiếu agent với brute-force. `browser_demo.py` bao gồm cả luồng thử hai màn mới. Các nhãn/clue của màn được lưu cố định trên server. Chưa có CNF cho hai loại mới; thành viên encoder/SAT cần bổ sung theo schema trên khi tích hợp. Không thay đổi `docs/assignment.md`.

### Walkthrough (server/local docs, không phục vụ vào gameplay)

**Đêm chuông câm, 3×3.** Mở sẵn A1 Vô can, A2 Sói. A1 chỉ C1 Vô can; C1 cho nhóm C1/C2 không Sói nên C2 Vô can. Sau hai nước dễ: A2 đếm đúng 1 trong `{B1,B2}`, C2 đếm đúng 1 trong `{B1,B2,C3}` ⇒ C3 Vô can. Hai clue là bắt buộc, không có clue đơn lẻ đang mở cho kết luận này. C3 đếm cột A ⇒ A3 Sói; A3 đếm hàng 3 ⇒ B3 Sói; SAME B3/B1 ⇒ B1 Sói; DIFFERENT B1/B2 ⇒ B2 Vô can. Tổng 7 lần lật hợp lệ.

**Tro tàn bên cổng Bắc, 4×4.** A1 đếm đúng 1 trong `{D1,B1,C1}`, A2 đếm đúng 2 trong `{B1,C1,A3}`. Tất cả bốn ô chưa biết: trừ hai ngân sách cho A3 − D1 = 1 ⇒ D1 Vô can, A3 Sói. Bỏ riêng từng clue thì D1 chưa bắt buộc; không có clue đơn lẻ cho kết luận. A3 mở B2 Vô can; ghép với clue D1 ⇒ B1 Sói. B1 đếm cột C không Sói, mở một đợt bốn ô Vô can. Các đếm hàng 2, hàng 3, cột D rồi hàng 4/cột A xác định các ô còn lại. Thứ tự demo row-major: D1, A3, B1, C1, B2, C2, D2, B3, C3, D3, A4, B4, C4, D4.

**Đêm trăng đỏ, 5×5.** A1 cho B1/B2 không Sói, hai nước đầu dễ. A2 đếm đúng 1 trong `{C1,D1}`, B1 đếm đúng 1 trong `{C1,D1,C3}` ⇒ C3 Vô can (bắt buộc cả hai clue). C3 đếm nhà kề E1 không Sói ⇒ D1/D2/E2 Vô can. Ghép ngân sách để mở C1/E1, hàng 2 mở C2, SAME mở A3. E2 loại Sói ở A4/C5/E5; các đếm cột A/hàng 5 và SAME A5/D5 đưa sang nửa dưới. Cột D, nhà kề E4, cột E, hàng 4 rồi nhà kề A3 hoàn tất. Không có chuỗi FACT nối tiếp; nhiều bước là ngân sách hàng/cột/ô kề.

**Bến sương mù, 5×5.** A1 cho A2/C2/D2 không Sói. Sau A2: E1 đếm đúng 1 trong `{A3,B3}`, A2 đếm đúng 1 trong `{A3,B3,C3}` ⇒ C3 Vô can (bắt buộc E1 và A2). Hàng 2 và nhà kề A1 xác định B2/E2/B1; E2 loại Sói ở D1/B3/E3. Hàng 1, hàng 3 và cột A mở các trục chính; C1 loại Sói ở C5/E5/B4. Cột B/E/D/C và nhà kề E3 hoàn tất. Các clue đều được mở trước khi dùng để phán người tiếp theo, không cần đọc clue dưới chính ô đang xét.

Các checkpoint được kiểm ở đúng public state bởi `tests/test_authored_cases.py`: kết luận forced; bỏ từng clue thì UNKNOWN; thử mọi clue đang mở đơn lẻ đều không ép target. Mỗi clue được đánh giá trực tiếp với nhãn authored. Agent hiện có giải hết từng màn từ `initial`, và kiểm toàn bộ clue + vai mở sẵn có một mô hình duy nhất. Không viết solver mới để làm những kiểm tra này.

## Kiểm thử và bằng chứng

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
# Trong cửa sổ khác, khởi động app.py trước các bài kiểm trình duyệt:
.\.venv\Scripts\python tests\browser_demo.py
.\.venv\Scripts\python tests\browser_fit.py
```

Hai script Chrome hỗ trợ `--url http://127.0.0.1:5001` để dùng server kiểm thử riêng. Test dữ liệu/backend hiện có 47 bài, gồm các kiểm tra extension và tính duy nhất độc lập. Browser demo kiểm sáu hồ sơ (gồm hai màn extension), điểm chứng minh thủ công, hai từ chối, Hint, Auto Solve từng bước, Load/Restart, giữ phiên, spotlight bật/tắt, Sổ tối và kiểm response không chứa vai/clue úp. Browser fit kiểm 1366×768 và 1440×900 ở zoom 100%, không có cuộn dọc bên trong bàn, hàng cuối phán được và popover đổi hướng; Sổ cuộn riêng; mobile/cửa sổ thấp cuộn tự nhiên.

Ảnh kiểm chứng local ở `tmp/qa/` (gitignore). Mobile là Chrome mô phỏng viewport, chưa kiểm thiết bị thật/Safari/Firefox/production. Test/API không phải chứng nhận bảo mật toàn diện. Không có thí nghiệm hay báo cáo cho mục 4.5/4.6 trong gói 4.1 này.

## Đối chiếu 4.1

| Dòng yêu cầu | Implementation / kiểm chứng |
| --- | --- |
| GUI, lưới, tọa độ, tên/nghề, vai biết, clue mở, thẻ úp | Web/Gridwolf; layout public, icon ba trạng thái; kiểm desktop/mobile. |
| Gọi CRIMINAL hoặc INNOCENT | Kết tội/Minh oan; giữ enum trong API. |
| Verdict proved + correct → mở và hiện clue | `GameEngine.verdict`, chung luồng chơi tay/Auto Solve; trace chỉ có nước đã chấp nhận. |
| Hai dạng từ chối không lộ clue | NOT_PROVABLE và CONTRADICTED riêng; so state trước/sau trong test. |
| Chọn clue, highlight đúng vùng | `paintSpotlight()` lấy public `cells`; bạc xám sáng, nhãn vai riêng, nút Bỏ soi/Esc/bấm lại. |
| Load / Restart / Hint / Auto Solve | API thật; Hint/Auto Solve đang dùng implementation có sẵn, factory cho nhóm thay adapter. |
| Engine giữ bí mật; agent chỉ nhận public knowledge | `knowledge()`/`view()` có ranh giới rõ; test adapter factory và response. |

## Ảnh nền và nguồn tham khảo

Cảnh nền gốc Gridwolf: `static/scenes/gridwolf-village-night.webp`, tạo bằng **built-in image_gen**, khoảng 206 KB. Hiển thị toàn cảnh ở Trang chủ, crop và phủ xanh đen trong gameplay. Người và sói trong tranh không liên hệ với cell/đáp án. Prompt cuối, chế độ tạo và xuất xứ được ghi nguyên văn trong [ASSET_NOTES.md](static/scenes/ASSET_NOTES.md). Không dùng screenshot, logo hoặc asset Agrou.

Tham khảo cách đọc nhóm/ngân sách từ [Griductive Strategy](https://knotwise.games/games/griductive/strategy) và cách hiểu hàng/cột/ô kề từ [How to Play](https://knotwise.games/games/griductive/how-to-play). Các nhân vật, clue, lời giải và cảnh Gridwolf được soạn riêng. Chưa tích hợp thuật toán CNF/DPLL của nhóm; phần demo hiện tại dùng đúng adapter đã có, không tuyên bố hoàn thành các mục thuật toán của toàn Project 2.

Nhân vật được xếp theo thứ tự tên ABC của dữ liệu màn, từ trái sang phải rồi từ trên xuống dưới; không trộn tên khi tải hoặc chơi lại.

## Danh sách nghề

Dùng 27 nghề do nhóm chọn; mỗi màn lấy đủ số nghề cần thiết, xoay thứ tự giữa các màn. Nghề chỉ giúp nhận diện nhân vật, không ảnh hưởng logic puzzle.

- Nông dân
- Thợ may
- Thợ đóng giày
- Ngư dân
- Thợ dệt
- Thợ rèn
- Thợ mộc
- Thợ làm nến
- Thợ xây
- Thợ làm bánh
- Thương nhân
- Đầu bếp
- Chủ quán rượu
- Người đưa thư
- Người chăn cừu
- Thợ mỏ
- Người làm vườn
- Thợ đóng thuyền
- Lính gác
- Thầy thuốc
- Người đánh xe ngựa
- Chủ nhà trọ
- Người lái đò
- Người nấu rượu
- Thợ làm gốm
- Tiều phu
- Nhà giả kim
