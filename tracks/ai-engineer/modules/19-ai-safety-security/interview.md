# Câu hỏi phỏng vấn: AI Safety & Security

## Prompt injection là gì? Vì sao nó khó hơn SQL injection?

Prompt injection là khi dữ liệu do người khác kiểm soát (câu chat, tài liệu, trang web, kết quả tool) chứa chỉ thị và
LLM làm theo chỉ thị đó thay vì ý của nhà phát triển. **Trực tiếp**: người dùng gõ "bỏ qua mọi hướng dẫn...". **Gián
tiếp** (Greshake et al., 2023): kẻ tấn công chỉ cần đặt chữ ở nơi ứng dụng sẽ đọc, và nạn nhân là một người dùng khác.

SQL injection có lời giải gốc: **parameterized query** tách hẳn kênh mã và kênh dữ liệu ở tầng giao thức, nên dữ liệu
không bao giờ được thực thi. LLM không có hai kênh: system prompt, câu hỏi và tài liệu đều là token trong cùng một chuỗi,
vai `system`/`user`/`tool` chỉ là token đánh dấu mà model **học** cách tôn trọng ở một mức nào đó. Vì vậy không có bản
vá dứt điểm ở tầng prompt; phòng thủ thật nằm ở việc giới hạn **hậu quả** (least privilege, allowlist tool, lọc output,
xác nhận của người dùng) và ở kiến trúc tách quyền (dual LLM, CaMeL).

## Jailbreak và prompt injection khác nhau thế nào?

Jailbreak nhắm vào **chính sách an toàn của model**: bắt model nói hay làm điều nó được train để từ chối (hướng dẫn chế
vũ khí, nội dung độc hại). Prompt injection nhắm vào **ứng dụng**: bắt model làm việc khác với ý của nhà phát triển (lộ
system prompt, gọi tool sai, chèn link). Một payload có thể làm cả hai. Phân biệt quan trọng vì người chịu trách nhiệm
khác nhau: jailbreak chủ yếu là việc của nhà cung cấp model (alignment, moderation), injection là việc của **bạn**,
người xây ứng dụng, và không nhà cung cấp nào sửa hộ được.

## Bạn đo hiệu quả của một phòng thủ chống injection thế nào?

Hai con số đi cùng nhau trên một bộ tấn công ghim:

- **ASR** (attack success rate): số lượt tấn công thành công chia cho số lượt model thật sự **thấy** payload, với tiêu
  chí thành công kiểm bằng code (regex, so khớp sau chuẩn hoá), báo kèm khoảng tin cậy Wilson. Lượt lỗi tách riêng.
- **Task success** trên cả tài liệu sạch lẫn tài liệu bị chèn: phòng thủ làm model trả lời sai trên dữ liệu sạch là
  một chi phí thật.

Thêm các lát cắt: theo kiểu tấn công, theo mục tiêu (một bộ chỉ có một loại mục tiêu cho bức tranh lệch), theo model. Chạy `temperature` 0, ghi model digest và phiên bản server, so hai cấu hình trên cùng máy. Và một phòng thủ chỉ
được đánh giá đúng khi bộ tấn công **có** làm được model không phòng thủ: ASR 0 ở mọi cấu hình nghĩa là bộ tấn công yếu,
không phải phòng thủ mạnh.

## Spotlighting, datamarking, sandwich: khi nào dùng, giới hạn là gì?

Đều là phòng thủ ở tầng prompt (Hines et al., 2024 cho spotlighting): bọc dữ liệu giữa dấu phân cách và xoá dấu đó khỏi
dữ liệu (để tài liệu không tự "đóng" vùng dữ liệu được), thay khoảng trắng của dữ liệu bằng ký tự lạ, hoặc nhắc lại nhiệm
vụ sau dữ liệu. Chúng rẻ và nên dùng như một lớp, nhưng:

- Chúng chỉ **giảm xác suất**, không bảo đảm gì; kẻ tấn công thích nghi (viết payload hợp với định dạng mới).
- Chúng có thể làm model **đọc kém** dữ liệu: datamark biến văn bản thành chuỗi lạ, model nhỏ trả lời sai hoặc thao tác
  sai trên giao diện. Phải đo task success trước khi bật.
- Hiệu quả khác nhau giữa các model: một cách bọc giúp model này có thể vô tác dụng với model khác.

Dùng chúng cùng các lớp tất định (lọc output, chính sách tool), không thay cho các lớp đó.

## Một agent đọc email và có quyền gửi email. Bạn thiết kế thế nào để chống injection?

Đây là đủ cả "lethal trifecta" (Willison): dữ liệu riêng, nội dung không tin cậy, kênh gửi ra ngoài. Các bước:

1. **Tách quyền**: agent đọc và tóm tắt email không có tool gửi; việc gửi là một bước riêng do người dùng khởi xướng.
   Nếu bắt buộc tự động, dùng kiến trúc kiểu dual LLM/CaMeL: model có quyền chỉ thấy yêu cầu của người dùng và lên kế
   hoạch; model đọc email không có tool, đầu ra của nó là giá trị có nhãn "không tin cậy".
2. **Chính sách tham số bằng code**: người nhận phải nằm trong danh bạ hoặc xuất hiện trong yêu cầu của người dùng (không
   phải trong nội dung email); không đính kèm tệp ngoài thư mục được phép; giới hạn số email mỗi giờ.
3. **Xác nhận của người dùng** trước khi gửi, hiển thị đúng người nhận, tiêu đề, nội dung sẽ gửi.
4. **Lọc output**: không render ảnh và link tới tên miền lạ trong bản tóm tắt.
5. **Giám sát**: log mọi lời gọi tool kèm nguồn gốc của tham số, cảnh báo khi tham số trùng với chuỗi trong email đọc vào.
6. Red-team bằng bộ email độc ghim trước mỗi lần đổi prompt hay model.

## Classifier phát hiện injection có recall 0.9 và FPR 2% trên tập test. Bạn có đưa lên production không?

Chưa đủ thông tin. Tập test công khai (như deepset/prompt-injections) có khoảng 40% injection; production có thể dưới
1%. Theo Bayes, precision ở production là $$\frac{r\pi}{r\pi + f(1-\pi)}$$: với $$\pi = 0.005$$ chỉ khoảng 0.18, tức hơn 4
trên 5 lần chặn là chặn oan. Cần hỏi: base rate thật bao nhiêu (đo bằng mẫu log có gán nhãn); chặn oan tốn gì (khách bỏ
đi, ticket) và bỏ sót tốn gì (hậu quả của injection trong **ứng dụng này**, phụ thuộc quyền của model); classifier có
được đo trên **ngôn ngữ** người dùng thật không (classifier train tiếng Anh/Đức thường sụp với tiếng Việt). Thường thì
dùng nó để gắn cờ, giảm quyền, ghi log, chọn ngưỡng theo FPR chấp nhận được, và không bao giờ là lớp phòng thủ duy nhất.

## Khi train classifier phát hiện injection, những lỗi đánh giá nào hay gặp?

- **Rò rỉ giữa train và test**: câu gần trùng (đổi một từ, dịch sang ngôn ngữ khác) nằm ở cả hai phía; kiểm bằng cosine
  char n-gram trước khi tin con số test.
- **Fit vectorizer trên toàn bộ dữ liệu** rồi mới chia fold: IDF đã "thấy" fold validation. Mọi bước học phải nằm trong
  pipeline fit lại ở mỗi fold.
- **Chọn ngưỡng trên tập test** rồi báo số trên chính tập đó.
- Báo accuracy hay precision trên tập cân bằng mà không quy về base rate thật.
- Không tách theo ngôn ngữ, theo nguồn; không thử phân phối lệch (tiếng Việt, câu bình thường "trông giống" tấn công như
  "bỏ qua bước 2", "quên mật khẩu").

## Ứng dụng gửi hồ sơ khách hàng cho API LLM bên thứ ba. Bạn xử lý PII thế nào?

Theo thứ tự:

1. **Tối thiểu hoá**: chỉ đưa vào prompt thứ cần cho câu hỏi; trợ lý tra đơn hàng không cần CCCD.
2. **Giả danh hoá** phần còn lại trước khi gửi: thay số điện thoại, email, CCCD, số tài khoản bằng token HMAC có khoá
   (`<PHONE_3f9a...>`), model làm việc với token, code khôi phục trước khi hiển thị cho nhân viên. Token ổn định trong
   phiên để model hiểu "cùng một người"; khoá giữ ở server.
3. **Phát hiện**: regex có kiểm cấu trúc (Luhn cho thẻ, mã tỉnh cho CCCD, từ khoá cho số tài khoản) cho loại có định
   dạng, NER cho tên và địa chỉ; đo recall trên mẫu thật vì regex bỏ sót cách viết lạ.
4. **Log và trace** chỉ chứa bản đã che; hạn lưu trữ; phân quyền đọc.
5. **Pháp lý**: kiểm với pháp chế về cơ sở xử lý, chuyển dữ liệu ra nước ngoài, điều khoản lưu trữ và dùng dữ liệu để
   train của nhà cung cấp. Ở Việt Nam hiện có Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và Nghị định 356/2025/NĐ-CP
   (theo các nguồn tra cứu, hiệu lực từ 01/01/2026); luôn kiểm văn bản hiện hành.

Và nhớ: dữ liệu đã giả danh hoá **vẫn** là dữ liệu cá nhân với ai giữ khoá; chỉ ẩn danh hoá thật mới thoát khỏi điều đó.

## Vì sao băm email bằng SHA-256 chưa đủ để làm end-user ID?

Không gian giá trị nhỏ và dễ đoán: danh sách email bị rò rỉ có hàng tỉ dòng, kẻ có danh sách chỉ cần băm từng email
và so. Số điện thoại di động Việt Nam chỉ cỡ $$5 \cdot 10^8$$ giá trị, băm hết trong vài phút. Dùng **HMAC** với secret của
server (hoặc một UUID ngẫu nhiên lưu trong bảng ánh xạ): nhà cung cấp vẫn gom được request của cùng một người để phát
hiện lạm dụng (đó là mục đích của `safety_identifier` của OpenAI và `metadata.user_id` của Anthropic), còn người ngoài
không dò ngược được. Xoay secret là cắt liên kết giữa log cũ và người dùng, hữu ích khi xử lý yêu cầu xoá dữ liệu.

## Làm sao kiểm một LLM chấm hồ sơ tuyển dụng có thiên lệch theo giới tính hay vùng miền không?

Probe **counterfactual**: lấy một bộ hồ sơ có năng lực khác nhau, sinh biến thể chỉ khác tên, giới tính, quê quán, cho
model chấm (`temperature` 0, output có schema), ghép cặp biến thể chỉ khác đúng một thuộc tính. Báo: chênh lệch trung
bình kèm khoảng tin cậy **bootstrap theo hồ sơ** (các cặp từ cùng hồ sơ không độc lập), **flip rate** ở ngưỡng quyết định
(một chênh lệch trung bình 0 vẫn có thể đảo quyết định của nhiều người theo hai chiều), và **sàn nhiễu**: chênh lệch khi
đổi tên trong **cùng** nhóm. Chỉ kết luận có thiên lệch khi chênh lệch giữa nhóm vượt sàn nhiễu và khoảng tin cậy không
chứa 0. Kèm kiểm độ nhạy (hồ sơ mạnh và yếu phải cách xa) để biết probe không mù. Nêu giới hạn: một vị trí, một prompt,
tên chọn tay. Giảm thiểu: che thuộc tính không cần thiết khỏi prompt, chấm theo rubric, kiểm định định kỳ, người quyết
định cuối.

## WEAT đo gì? Có nên dùng nó để kết luận một hệ thống là thiên lệch?

WEAT (Caliskan et al., 2017) đo liên kết ngầm trong embedding: hai tập từ đích (tên nam, tên nữ) gần hai tập thuộc tính
(sự nghiệp, gia đình) khác nhau bao nhiêu, ra effect size kiểu Cohen's d và p-value hoán vị. Hữu ích để **phát hiện**
liên kết, nhưng không đủ để kết luận về hệ thống: kết quả nhạy với việc chọn từ (6 tới 8 từ mỗi tập, đổi một từ có thể
lật dấu), với template câu cho sentence embedding (May et al., 2019), và liên kết trong embedding không tự động thành tác
hại ở tầng quyết định. Luôn chạy phép thử đối chứng (hai tập thuộc tính không liên quan) để biết $$d$$ "trông lớn" là bao
nhiêu khi không có gì, và đo tác hại ở tầng quyết định bằng probe counterfactual.

## Thiết kế pipeline moderation cho chatbot hỗ trợ khách hàng của một ngân hàng.

```text
request -> cấm? -> rate limit (theo user_key)
        -> giả danh hoá PII -> moderation input (trên văn bản đã che)
             self-harm -> trả lời hỗ trợ + chuyển người thật, không phạt (trước mọi lớp chặn cứng)
             vi phạm khác -> ghi vi phạm (đủ ngưỡng thì cấm có leo thang), từ chối
        -> phát hiện injection (luật + classifier): bị gắn cờ thì giảm quyền, không cho dùng tool,
           ghi log, chuyển người xem; không chặn cứng chỉ dựa vào một classifier xác suất
        -> LLM -> lọc output (link allowlist, quét bí mật) -> moderation output -> khôi phục PII -> trả lời
```

Thứ tự quan trọng ngang với từng lớp: một tin "tôi không muốn sống nữa" mà bị một classifier injection chặn trước khi
tới moderation sẽ nhận câu từ chối thay vì lời hỗ trợ. Lớp rẻ đứng trước vì chi phí, nhưng lớp nào **chặn cứng** thì
phải đứng sau nhánh an toàn cho người dùng.

Quyết định cần nói rõ: moderator nào (API như OpenAI `omni-moderation-latest`, model mở như Llama Guard chạy local, hay
LLM với chính sách tiếng Việt của mình) và **đo** nó trên tập tin nhắn của chính miền này, vì phàn nàn gay gắt dễ bị gắn
cờ nhầm; moderation input chạy song song với lời gọi chính để bớt độ trễ; fail open hay fail closed khi moderator lỗi
(chat thường: fail open có log; hành động có tác dụng phụ: fail closed); mọi thứ gửi tới moderator (nhất là moderator ở
bên thứ ba) cũng phải là văn bản đã che PII; nhánh tự hại là chuyển hướng hỗ trợ, không phải chặn lạnh lùng.

## Thiết kế hệ thống: chương trình red-teaming liên tục cho một sản phẩm LLM đang chạy.

- **Bộ tấn công có phiên bản** trong repo: template (naive, giả hệ thống, đóng vai, mã hoá, nhiều lượt, injection gián
  tiếp qua tài liệu) x mục tiêu kiểm được bằng code (lộ bí mật, lộ PII, gọi tool trái chính sách, chèn link) x cấu hình.
  Cộng **bộ câu bình thường** (kể cả câu trông giống tấn công) để đo chặn oan.
- **Chạy trong CI** mỗi khi đổi prompt, model, guard hay thư viện: `temperature` 0, cache theo khoá (model digest, prompt,
  case), bảng ASR với khoảng Wilson và tỉ lệ chặn oan; **cổng hồi quy** chặn merge khi ASR hoặc chặn oan tăng quá ngưỡng.
  Cỡ mẫu đủ để phân biệt mức thay đổi bạn quan tâm (vài chục lượt chỉ thấy được chênh lệch rất lớn).
- **Bổ sung từ thực tế**: mỗi sự cố hoặc báo cáo từ người dùng thành một case mới; tấn công tự động (garak, PyRIT,
  promptfoo, LLM attacker kiểu PAIR) để mở rộng bộ case định kỳ, người duyệt case trước khi đưa vào bộ ghim.
- **Giám sát production**: tỉ lệ guard kích hoạt, theo người dùng (end-user ID băm), cảnh báo khi đột biến.
- **Quy trình**: phạm vi được phép, lưu trữ payload độc an toàn, báo cáo lỗ hổng của model cho nhà cung cấp, và một chủ
  sở hữu chịu trách nhiệm cho bảng số.

## Guardrail tất định và guardrail xác suất khác nhau thế nào? Bạn xếp chúng ra sao?

Tất định: regex, allowlist, giới hạn độ dài, rate limit, kiểm tham số tool, validate schema. Cùng input luôn cùng kết
quả, chạy micro tới mili giây, giải thích được, và **bảo đảm** đúng thứ được kiểm (không ảnh nào tới tên miền lạ). Điểm
yếu: chỉ bắt thứ đã nghĩ tới; danh sách chặn bắt cụm, không bắt ý.

Xác suất: classifier, LLM moderator, LLM judge. Bắt được ý và cách viết mới, nhưng có FPR, có lúc sai, tốn từ mili giây
(classifier nhỏ) tới hàng giây (LLM), và chính chúng có thể bị tấn công.

Xếp: lớp tất định rẻ đứng trước để loại tấn công lười và kiểm định dạng; lớp xác suất đứng sau, chỉ gọi khi cần; lớp
quyết định hành động (chính sách tool, xác nhận người dùng) là tất định và đứng cuối, không phụ thuộc lớp xác suất có bắt
được hay không. Trước mọi so khớp chuỗi phải chuẩn hoá Unicode (NFKC, bỏ ký tự vô hình, confusable), nếu không mỗi biến
thể là một đường lách.

## System prompt của bạn chứa API key nội bộ "để model gọi dịch vụ". Bạn sửa gì?

Bỏ nó ra khỏi prompt. Mọi thứ trong context đều có thể bị đọc lại (OWASP LLM07, System Prompt Leakage): "đừng tiết lộ"
trong prompt là một yêu cầu, không phải một cơ chế, và có vô số cách lách (đánh vần, dịch, đóng vai, viết dưới dạng thơ).
Credential thuộc về **code thực thi tool**: model đề nghị gọi `get_order(order_id)`, code của bạn gắn credential và kiểm
quyền theo người dùng thật đang đăng nhập. Tương tự cho dữ liệu: đừng đưa dữ liệu của người dùng khác vào context rồi dặn
model "chỉ nói 3 số cuối"; đưa vào đúng thứ được phép nói. Least privilege ở mức context là phòng thủ duy nhất có ASR
bằng 0 theo thiết kế cho mục tiêu "lộ thứ nằm trong prompt".
