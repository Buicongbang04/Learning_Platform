# Câu hỏi phỏng vấn: Econometrics & Regression

## Những giả định nào của OLS thật sự quan trọng, và vỡ thì hỏng cái gì?

Chia làm hai nhóm, vì chúng hỏng những thứ khác nhau:

- **Quyết định hệ số có đúng không**: dạng hàm đúng (tuyến tính theo tham số) và exogeneity
  $$E[\varepsilon \mid X] = 0$$. Vỡ exogeneity (thiếu biến, sai số đo lường ở x, quan hệ hai chiều)
  thì $$\hat\beta$$ bias, và thêm dữ liệu không sửa được.
- **Quyết định SE, p-value, CI có đúng không**: homoskedasticity và sai số độc lập. Vỡ thì
  $$\hat\beta$$ vẫn không bias nhưng SE sai, thường là quá nhỏ. Sửa bằng robust SE (HC3) hoặc
  cluster SE.

Phân phối chuẩn của sai số gần như không quan trọng khi mẫu lớn (CLT cho $$\hat\beta$$ xấp xỉ
chuẩn). Ứng viên junior hay chạy Shapiro-Wilk trên residual của 100 nghìn dòng rồi lo lắng; ứng
viên senior hỏi "các quan sát này có độc lập không, hay nhiều đơn đến từ cùng một seller?".

Gauss-Markov nói thêm: khi đủ các giả định (trừ chuẩn), OLS là BLUE (tốt nhất trong các ước lượng
tuyến tính không bias). Điều đó ít quan trọng trong thực tế bằng việc biết giả định nào đang vỡ.

## Hệ số trong model log-log nghĩa là gì? Còn biến dummy trong model log y?

- `log y ~ log x`: **elasticity**. x tăng 1% thì y tăng khoảng β%. Trên Olist, hệ số của log
  khoảng cách trong model phí ship là 0.1418: khoảng cách gấp đôi thì phí ship nhân
  $$2^{0.1418} \approx 1.103$$, tăng 10.3%.
- `log y ~ dummy`: y nhân $$e^{\beta}$$ khi dummy bật. Cùng bang có β = −0.2242, tức phí ship thấp
  hơn $$1 - e^{-0.2242} \approx 20.1\%$$. Dùng "β × 100%" (−22.4%) chỉ xấp xỉ đúng khi β nhỏ.
- `y ~ log x`: x tăng 1% thì y tăng β/100 đơn vị.

Bẫy khi dự đoán: $$e^{\widehat{\log y}}$$ ước lượng median của y, không phải mean. Muốn mean (ví
dụ tổng phí ship dự kiến), nhân với hệ số smearing của Duan (trung bình của $$e^{\hat\varepsilon}$$)
hoặc dùng GLM Gamma với log link, model trực tiếp $$\log E[y]$$.

## R² cao có nghĩa là model tốt không? R² thấp có sao không?

Không, và tuỳ mục đích.

- R² chỉ so được giữa các model có **cùng y**. Model phí ship tuyến tính có R² 0.588, model log có
  0.655, nhưng không thể kết luận model log "tốt hơn" từ hai con số này: một cái giải thích variance
  của BRL, cái kia variance của log BRL.
- Với mục đích mô tả hoặc nhân quả, R² thấp không sao: hồi quy lương theo số năm học có R² thấp vì
  lương phụ thuộc nhiều thứ khác, nhưng hệ số giáo dục vẫn có thể ước lượng chính xác. Ngược lại R²
  cao không cứu được một hệ số bị omitted variable bias.
- Với mục đích dự đoán, đánh giá trên test set (chia theo thời gian), không trên R² in-sample. R²
  luôn tăng khi thêm biến; adjusted R² phạt nhẹ, nhưng validation mới là thước đo thật.
- R² gần 1 trong dữ liệu kinh doanh thường là dấu hiệu leakage (một biến là biến đổi của y) hoặc
  hai chuỗi thời gian cùng xu hướng (spurious regression, module 07).

## Heteroskedasticity là gì? Bạn xử lý thế nào, và chọn HC0, HC1 hay HC3?

Variance của sai số thay đổi theo x: đơn giá cao có phí ship biến động hơn, doanh nghiệp lớn có đầu
tư biến động hơn. Hệ số OLS vẫn không bias, nhưng công thức SE cổ điển sai.

Cách phát hiện: vẽ residual vs fitted (hình phễu), Breusch-Pagan hoặc White test. Nhưng với dữ liệu
lớn, test gần như luôn bác bỏ, nên thực tế là **mặc định dùng robust SE** và chỉ dùng SE cổ điển khi
có lý do.

- HC0 là sandwich gốc của White, hơi nhỏ ở mẫu nhỏ.
- HC1 nhân thêm $$n/(n-k)$$, là `robust` của Stata.
- HC3 chia mỗi residual bình phương cho $$(1-h_{ii})^2$$, phạt các điểm leverage cao; hoạt động
  tốt nhất ở mẫu nhỏ và trung bình. Đây là mặc định nên chọn.

Trên Olist, model tuyến tính của phí ship có SE HC3 gấp 3.3 lần SE cổ điển ở hệ số cân nặng. Lựa
chọn khác: biến đổi y (log làm tỉ lệ đó xuống còn 0.91–1.17), hoặc WLS nếu biết dạng variance (hiệu
quả hơn nhưng sai dạng thì tệ hơn).

## Khi nào cần cluster SE? Cluster ở cấp nào?

Khi các quan sát trong cùng nhóm có sai số tương quan: đơn của cùng seller, giao dịch của cùng khách,
học sinh cùng lớp, các năm của cùng công ty. Robust SE (HC) không xử lý được, vì nó vẫn giả định các
quan sát độc lập.

Cấp cluster: cấp mà bạn tin sai số tương quan, và **ít nhất** là cấp mà treatment được gán (random
theo cửa hàng thì cluster theo cửa hàng, dù dữ liệu ở cấp giao dịch). Khi không chắc, chọn cấp lớn
hơn, miễn còn đủ cluster.

Ví dụ thật: model log phí ship trên 86 065 đơn Olist, cluster theo 2 879 seller làm SE tăng 3.5–8.7
lần. Grunfeld: SE fixed effects của `capital` từ 0.0165 lên 0.0501 khi cluster theo công ty.

Giới hạn: cluster SE cần nhiều cluster (quy tắc ngón tay cái: từ 30–50 trở lên). Với 11 công ty như
Grunfeld, cluster SE cũng không đáng tin; dùng wild cluster bootstrap hoặc nói rõ giới hạn.

## Multicollinearity là gì? Khi nào nó là vấn đề và bạn làm gì?

Các biến giải thích tương quan mạnh với nhau, nên dữ liệu không đủ thông tin để tách tác động riêng
của từng biến. Dấu hiệu: SE lớn, hệ số đổi dấu khi thêm bớt biến, F test cả nhóm có ý nghĩa nhưng
từng hệ số không. Đo bằng VIF $$= 1/(1 - R_j^2)$$: variance của $$\hat\beta_j$$ bị nhân lên đúng VIF
lần.

Nó **không** là vấn đề khi: mục đích là dự đoán; hoặc các biến tương quan chỉ là biến kiểm soát và
biến quan tâm không tương quan mạnh với chúng.

Xử lý theo thứ tự ưu tiên: (1) hỏi có cần tách hai tác động không; nếu không, gộp (cân nặng và thể
tích thành cân nặng tính cước); (2) Ridge nếu dự đoán; (3) chấp nhận SE lớn và báo cáo trung thực.
Không bỏ biến chỉ vì VIF > 10: bỏ một confounder là đổi variance lấy bias.

Một lỗi kỹ thuật hay gặp: gọi `variance_inflation_factor` của statsmodels mà không thêm cột hằng
số, mọi VIF đều lớn giả tạo.

## Omitted variable bias là gì? Cho ví dụ và cho biết hướng của bias.

Bỏ sót biến $$x_2$$ vừa ảnh hưởng y vừa tương quan với biến quan tâm $$x_1$$ thì hệ số của $$x_1$$
hấp thụ một phần tác động của $$x_2$$:

$$
\mathrm{plim}\,\hat\beta_1 = \beta_1 + \beta_2 \cdot \frac{\mathrm{Cov}(x_1, x_2)}{\mathrm{Var}(x_1)}
$$

Hướng bias = dấu của $$\beta_2$$ × dấu của tương quan. Ví dụ Olist: phí ship theo log khoảng cách.
Bỏ biến "cùng bang" (β₂ âm: cùng bang rẻ hơn; tương quan với khoảng cách âm: cùng bang thì gần) thì
bias dương. Thực tế: hệ số khoảng cách từ 0.1418 lên 0.2001.

Câu trả lời senior thêm: OVB không kiểm được bằng thống kê từ chính dữ liệu, vì biến bị bỏ không có
trong dữ liệu. Cách đối phó: lập luận về dấu bias để biết ước lượng là cận trên hay cận dưới, phân
tích độ nhạy (cần confounder mạnh cỡ nào để xoá kết quả), panel fixed effects cho phần không đổi theo
thời gian, hoặc thiết kế nhân quả (module 06).

## Odds ratio 13 có nghĩa là "khả năng gấp 13 lần" không? Logistic hay linear probability model?

Không. Trên Olist, logistic review xấu theo giao trễ (cùng vài biến kiểm soát) cho OR = 13.1. Nhưng
xác suất review xấu là 54.1% ở đơn trễ và 9.2% ở đơn đúng hẹn: gấp khoảng 6 lần. Odds là
$$p/(1-p)$$: 1.18 so với 0.10. OR chỉ xấp xỉ tỉ lệ xác suất khi biến cố hiếm (dưới khoảng 10%).

Cách trình bày cho stakeholder: **average marginal effect** (thay đổi xác suất). Với biến 0/1 phải
tính rời rạc: dự đoán cho mọi đơn khi `late=1` và khi `late=0`, lấy chênh lệch trung bình: +45.4 điểm
phần trăm. `get_margeff()` mặc định coi biến là liên tục và cho +24.1, sai.

Linear probability model (OLS trên 0/1, robust SE) cho hệ số 0.454, gần như trùng AME. Ưu: dễ đọc,
hệ số là thay đổi xác suất, dùng thẳng với fixed effects. Nhược: dự đoán có thể ra ngoài [0, 1],
heteroskedastic theo cấu trúc (luôn cần robust SE). Dùng logistic khi mục đích là dự đoán xác suất,
nhất là gần 0 hoặc 1; dùng LPM thoải mái khi mục đích là ước lượng tác động trung bình.

## Poisson hay Negative Binomial? Làm sao biết có overdispersion?

Poisson ép $$\mathrm{Var}(y) = E[y]$$. Dữ liệu đếm trong kinh doanh hầu như luôn có variance lớn hơn
mean (khách khác nhau rất nhiều). Kiểm tra: Pearson $$\chi^2$$ / df của model Poisson; xa 1 nhiều
(1.5 trở lên) là overdispersion.

Olist: số món thêm mỗi đơn có mean 0.142, variance 0.290; Pearson $$\chi^2$$/df = 1.98.

Hậu quả và lựa chọn:

- Hệ số Poisson vẫn nhất quán nếu dạng của mean đúng (quasi-MLE), chỉ SE sai: SE cổ điển 0.0097 so
  với robust 0.0150. **Poisson + robust SE** là lựa chọn an toàn khi chỉ cần hệ số.
- **Negative Binomial** model thêm $$\mathrm{Var} = \mu + \alpha\mu^2$$, cho dự đoán phân phối tốt
  hơn (AIC 78 047 so với 87 399), cần khi quan tâm xác suất từng giá trị (bao nhiêu % đơn có từ 3
  món).
- Quá nhiều số 0 so với cả hai (Olist: 90.0% đơn chỉ một món, Poisson dự đoán 86.7%) và số 0 có cơ
  chế riêng: zero-inflated hoặc hurdle model.

Diễn giải hệ số với log link: $$e^{\beta}$$ là incidence rate ratio. Hệ số −0.389 của log giá trung
bình mỗi món nghĩa là giá gấp $$e$$ lần thì số món thêm nhân 0.678.

## Bạn fit một phân phối cho dữ liệu thế nào? Chọn giữa lognormal và gamma bằng cách nào?

1. Nhìn dữ liệu: dương? lệch phải? histogram của log x có gần đối xứng không?
2. Fit bằng MLE. Lognormal có nghiệm đóng (mean và std ddof=0 của log x). Gamma cần tối ưu số;
   trong scipy nhớ `floc=0`.
3. So sánh: log-likelihood / AIC (cùng số tham số thì như nhau), **QQ-plot** để thấy lệch ở thân
   hay đuôi, KS statistic như một khoảng cách.
4. Kiểm phần quan trọng cho mục đích: nếu cần xác suất đuôi, so trực tiếp tỉ lệ thực tế vượt ngưỡng.

Giá trị đơn Olist (96 470 đơn): lognormal AIC 1 137 571, gamma 1 164 674, lognormal thắng. Nhưng
P(đơn > 1 000 BRL): thực tế 1.15%, lognormal 0.30%, gamma 0.04%. Phân phối thắng AIC vẫn đánh giá
thấp đuôi gần 4 lần. Dùng nó để mô phỏng rủi ro đơn lớn sẽ sai. AIC bị chi phối bởi thân phân phối,
nơi có nhiều điểm nhất.

## KS test cho p-value 1e-57, vậy dữ liệu không phải lognormal à?

Không phải lognormal **tuyệt đối**, đúng, nhưng chẳng dữ liệu thật nào đúng tuyệt đối một phân phối
tham số. Với 96 470 đơn, KS phát hiện được cả những lệch rất nhỏ: statistic chỉ 0.026 (CDF lệch tối
đa 2.6 điểm phần trăm), nhưng p ≈ 7.8e-57. Lấy ngẫu nhiên 500 đơn, cùng phân phối cho p = 0.78.

Hai điểm nữa:

- Khi tham số được ước lượng từ chính dữ liệu, p-value KS chuẩn **quá lớn** (test dễ dãi). Cần
  Lilliefors hoặc parametric bootstrap nếu thật sự cần p-value.
- Câu hỏi đúng là "lệch ở đâu và có ảnh hưởng tới quyết định không", được trả lời bằng QQ-plot và
  so sánh trực tiếp đại lượng cần dùng (quantile, xác suất đuôi), không phải bằng p-value.

## Đọc QQ-plot thế nào?

Trục ngang là quantile lý thuyết, trục dọc là quantile mẫu. Đúng phân phối thì điểm nằm trên đường
chéo.

- Hai đầu cong lên trên ở phải và xuống dưới ở trái (hình chữ S ngược): đuôi **nặng** hơn lý thuyết.
- Hai đầu cong vào trong: đuôi nhẹ hơn.
- Cả đường cong một chiều (hình cung): lệch (skew) khác lý thuyết.
- Lệch ở một vùng giữa: có thể là mixture hoặc giá trị bị làm tròn (giá 99.90, 49.90).

Với giá trị đơn Olist, QQ của log giá trị đơn (chuẩn hoá) với phân phối chuẩn gần thẳng ở thân
(quantile 25% và 75%: −0.70 và 0.60 so với ±0.67), nhưng cả hai đầu nằm **trên** đường chéo:
quantile 99.9% là 3.79 so với 3.09 (đuôi phải nặng hơn lognormal), quantile 0.1% là −2.35 so với
−3.09 (đuôi trái nhẹ hơn: hầu như không có đơn quá nhỏ vì luôn cộng phí ship). Hình cung đó nghĩa là
log giá trị đơn vẫn còn lệch phải, khớp với việc lognormal đánh giá thấp P(đơn > 1 000 BRL).

## Fixed effects khác random effects thế nào? Bạn chọn thế nào?

Cả hai cho mỗi đơn vị một hằng số riêng $$\alpha_i$$. Fixed effects cho phép $$\alpha_i$$ tương quan
tuỳ ý với x, ước lượng chỉ từ biến thiên trong từng đơn vị (within). Random effects giả định
$$\alpha_i$$ không tương quan với x, dùng cả biến thiên giữa các đơn vị nên hiệu quả hơn, nhưng bias
nếu giả định sai.

Hausman test: nếu RE đúng thì hai ước lượng gần nhau; chênh lệch lớn bác bỏ RE. Grunfeld: FE cho
`value` 0.1101, `capital` 0.3100; RE cho 0.1093, 0.3080; Hausman 3.97, p = 0.138, không bác bỏ.

Trong thực tế với dữ liệu quan sát:

- Chọn FE khi lo $$\alpha_i$$ tương quan với x (gần như luôn là vậy với seller, công ty, khách) và x
  thay đổi đủ theo thời gian.
- RE khi cần hệ số của biến không đổi theo thời gian (vùng miền, giới tính) và có lý do tin giả định,
  hoặc dùng correlated random effects (Mundlak: thêm trung bình theo đơn vị của x vào RE).
- Hausman có power thấp khi ít đơn vị (11 công ty), và bản cổ điển không dùng robust SE. Không bác
  bỏ không có nghĩa là RE đúng.

Dù chọn gì: cluster SE theo đơn vị.

## Fixed effects không xử lý được những gì?

- **Thứ thay đổi theo thời gian** mà không đo được: seller đổi đơn vị vận chuyển giữa chừng làm cả
  tỉ lệ trễ và chất lượng đóng gói đổi cùng lúc.
- **Hệ số của biến không đổi theo thời gian** bị hấp thụ hết vào $$\alpha_i$$.
- **Reverse causality trong cùng kỳ**: review xấu tháng này làm seller đổi cách giao.
- **Sai số đo lường** bị khuếch đại: sau khi demean, biến thiên còn lại nhỏ, nhiễu chiếm phần lớn,
  hệ số bị kéo về 0 (attenuation).
- **Hiệu ứng động**: model có biến trễ của y cộng FE bị bias khi T nhỏ (Nickell bias); cần
  Arellano-Bond hoặc T lớn.
- Two-way FE với treatment bật ở các thời điểm khác nhau và tác động thay đổi theo thời gian cho
  trọng số âm (Goodman-Bacon); dùng các estimator DiD mới (module 06).

## Bạn xử lý outlier và điểm ảnh hưởng trong hồi quy thế nào?

1. Tách hai khái niệm: **outlier** (residual lớn), **leverage** (x xa tâm), **influence** (bỏ điểm
   đó thì hệ số đổi nhiều; đo bằng Cook's distance). Điểm nguy hiểm là leverage cao **và** residual
   lớn.
2. Điều tra trước khi xử lý: lỗi dữ liệu (cân nặng 0 g, giá 0.85 BRL kèm sản phẩm 30 kg), hay giá trị
   thật hiếm? Lỗi thì sửa hoặc loại, kèm ghi lại quy tắc.
3. Giá trị thật: không xoá. Dùng biến đổi (log), robust regression (Huber), winsorize có báo cáo,
   hoặc model riêng cho phần đó.
4. Báo cáo kết quả có và không có các điểm đó. Kết luận lật ngược nhờ vài điểm thì kết luận yếu.

Với dữ liệu lớn, ngưỡng $$4/n$$ của Cook's distance gắn cờ hàng nghìn điểm (model phí ship: 5 601
đơn, 6.5%) nhưng Cook's lớn nhất chỉ 0.005. Không điểm nào một mình kéo được model; influence lúc
này là công cụ tìm dữ liệu bẩn.

## Case: PM thấy sản phẩm có nhiều ảnh bán chạy hơn, hồi quy cho hệ số dương có ý nghĩa, muốn bắt mọi seller đăng thêm ảnh. Bạn nói gì?

Hệ số đó là **association**, chưa phải tác động. Các giải thích khác cho cùng một con số:

- **Confounding**: seller chuyên nghiệp vừa chụp nhiều ảnh, vừa có giá tốt, mô tả kỹ, giao nhanh,
  phản hồi khách nhanh. Seller FE (panel seller × sản phẩm) loại được phần không đổi của seller,
  nhưng không loại được sản phẩm "hot" được đầu tư nhiều ảnh hơn.
- **Reverse causality**: sản phẩm bán chạy thì seller mới đầu tư chụp thêm ảnh.
- **Selection**: sản phẩm bán kém bị gỡ khỏi sàn, chỉ còn lại sản phẩm tồn tại đủ lâu.

Đề xuất theo thứ tự chi phí: (1) xem panel seller × sản phẩm × tháng, sản phẩm **thêm ảnh** giữa
chừng có tăng bán so với trước và so với sản phẩm tương tự không (event study, module 06); (2) tốt
nhất là A/B test: hiển thị thêm ảnh (ảnh đã có sẵn nhưng giấu bớt) cho ngẫu nhiên một nửa khách;
(3) nếu chưa làm được, chạy pilot với nhóm seller tự nguyện, cảnh báo selection bias.

Nói với PM bằng ngôn ngữ của họ: "Có thể đúng, nhưng con số hiện tại không phân biệt được 'ảnh làm
tăng bán' với 'seller giỏi thì vừa nhiều ảnh vừa bán chạy'. Bắt mọi seller đăng ảnh tốn công của
seller; trước đó nên kiểm bằng một thí nghiệm hai tuần."

## Case: Đội logistics Olist muốn biết seller nào tính phí ship "quá cao". Bạn làm thế nào?

1. **Định nghĩa "quá cao" so với cái gì**: so với phí kỳ vọng của một món cùng cân nặng, kích thước,
   khoảng cách, tuyến (cùng bang hay không). Đó là model phí ship: `log_freight` theo log cân nặng,
   log thể tích, log khoảng cách, cùng bang (và nên thêm cặp bang gửi – nhận, vì giá cước theo tuyến).
2. **Đơn vị so sánh** là seller, nên tính residual trung bình mỗi seller. Nhưng residual trung bình
   của seller có 3 đơn nhiễu hơn nhiều so với seller có 3 000 đơn: dùng shrinkage (random effects /
   empirical Bayes) hoặc chỉ gắn cờ khi CI của residual trung bình nằm trên ngưỡng.
3. **Mức kinh doanh**: residual log 0.2 nghĩa là phí cao hơn kỳ vọng khoảng 22%. Đặt ngưỡng cùng đội
   logistics, nhân với số đơn để ưu tiên seller ảnh hưởng nhiều khách nhất.
4. **Giải thích trước khi kết tội**: seller ở vùng xa trung tâm, dùng dịch vụ nhanh, hàng cồng kềnh
   khó đóng gói. Model thiếu biến thì residual phản ánh biến thiếu, không phải "tính giá cao".
5. SE: cluster theo seller khi báo cáo hệ số model (SE tăng 3.5–8.7 lần trên dữ liệu thật).

Kết quả là danh sách để **điều tra**, không phải danh sách phạt.

## Case: Logistic cho OR của giao trễ lên review xấu là 13. Lãnh đạo hỏi: "giảm giao trễ một nửa thì review xấu giảm bao nhiêu?"

Trả lời có hai phần: con số, và độ tin cậy của con số.

Con số theo model: AME rời rạc của giao trễ là +45.4 điểm phần trăm. Tỉ lệ trễ 8.1%; giảm một nửa
là bớt khoảng 4 điểm phần trăm đơn trễ, nhân 45 điểm: review xấu giảm khoảng 1.8 điểm phần trăm, từ
12.8% xuống khoảng 11%. Với stakeholder: "khoảng 1 trên 7 review xấu sẽ biến mất".

Độ tin cậy: đó là con số **nếu** quan hệ là nhân quả và các đơn bớt trễ giống các đơn trễ hiện tại.
Lý do nghi ngờ:

- Đơn trễ tập trung ở vùng xa, seller kém, mùa cao điểm; một phần review xấu do những thứ đó (seller
  kém thì hàng cũng kém). Panel seller × tháng với seller FE là bước đầu để loại phần không đổi của
  seller (bài Advanced 02: hệ số giảm từ 0.54 pooled còn 0.51 với seller FE, 0.48 khi thêm time FE).
- Cách giảm trễ quan trọng: nới ngày hẹn giao (ước tính dễ hơn) khác hẳn giao nhanh hơn. Nới ngày
  hẹn làm "đơn trễ" giảm theo định nghĩa nhưng khách có thể vẫn bực vì chờ lâu.

Khuyến nghị: dùng con số 1.8 điểm như cận trên định hướng; đo thật bằng thí nghiệm (thay đổi cách
ước tính ngày giao cho ngẫu nhiên một phần đơn) như module 03.

## Case: Bạn có 5 triệu dòng, mọi hệ số đều p < 0.001. Bạn báo cáo gì?

Với 5 triệu dòng, p-value gần như vô nghĩa để phân biệt cái quan trọng với cái không: mọi tác động
khác 0 một chút đều "có ý nghĩa". Báo cáo thay vào đó:

1. **Độ lớn kinh tế**: hệ số quy ra đơn vị kinh doanh (BRL, điểm phần trăm, % thay đổi) và so với
   ngưỡng hành động. Hệ số làm phí ship đổi 0.3% không đáng một cuộc họp.
2. **SE đúng**: 5 triệu dòng thường không phải 5 triệu quan sát độc lập (vài nghìn seller, vài trăm
   nghìn khách). Cluster SE có thể lớn gấp nhiều lần; sau khi cluster, một số hệ số hết "chắc".
3. **Robustness**: hệ số có giữ dấu và độ lớn qua các spec hợp lý (thêm biến kiểm soát, thêm FE,
   đổi dạng hàm, bỏ giai đoạn bất thường) không. Đây là nơi bias lộ ra, thứ mà dữ liệu lớn không sửa.
4. **Bias, không phải variance, là rủi ro chính**: với dữ liệu lớn, CI hẹp quanh một con số có thể
   sai. Nói rõ giả định nhân quả nào cần để diễn giải.

Một câu tóm cho stakeholder: "Chúng tôi chắc chắn về dấu; độ lớn nằm trong khoảng X–Y qua các cách
tính; cái chúng tôi chưa chắc là đây có phải nhân quả hay không."
