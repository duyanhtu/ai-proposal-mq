import json
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict, Annotated

# Your imports
from app.nodes.states.state_finance import StateSqlFinance

# SQL Expert Prompt

# Fetch schema info


sqlSchema_financial_results = """
CREATE TABLE public.financial_results (
	id serial4 NOT NULL,
	total_assets numeric NULL,
	total_liabilities numeric NULL,
	short_term_assets numeric NULL,
	short_term_liabilities numeric NULL,
	net_asset_value numeric NULL,
	working_capital numeric NULL,
	revenue numeric NULL,
	profit_before_tax numeric NULL,
	profit_after_tax numeric NULL,
	has_financial_report bool NULL,
	financial_report_url text NULL,
	has_tax_declaration bool NULL,
	tax_declaration_url text NULL,
	has_tax_payment bool NULL,
	tax_payment_url text NULL,
	financial_year_to date NULL,
	financial_year_from date NULL,
	CONSTRAINT financial_results_pk PRIMARY KEY (id)
);

Below are 5 sample records
"id"	"total_assets"	"total_liabilities"	"short_term_assets"	"short_term_liabilities"	"net_asset_value"	"working_capital"	"revenue"	"profit_before_tax"	"profit_after_tax"	"has_financial_report"	"financial_report_url"	"has_tax_declaration"	"tax_declaration_url"	"has_tax_payment"	"tax_payment_url"	"financial_year_to"	"financial_year_from"
12	"5000000000000"	"2000000000000"	"1500000000000"	"800000000000"	"3000000000000"	"700000000000"	"1300000000000"	"100000000000"	"80000000000"	"true"	"/reports/bctc_2024.pdf"	"true"	"/reports/nop_thue_2024.pdf"	"true"	"/reports/qtt_2024.pdf"	"2024-03-31"	"2023-04-01"
13	"4800000000000"	"1900000000000"	"1400000000000"	"750000000000"	"2900000000000"	"650000000000"	"1156000000000"	"95000000000"	"76000000000"	"true"	"/reports/bctc_2022.pdf"	"true"	"/reports/nop_thue_2022.pdf"	"true"	"/reports/qtt_2022.pdf"	"2023-03-31"	"2022-04-01"
14	"4600000000000"	"1800000000000"	"1300000000000"	"700000000000"	"2800000000000"	"600000000000"	"1172000000000"	"90000000000"	"72000000000"	"true"	"/reports/bctc_2021.pdf"	"true"	"/reports/nop_thue_2021.pdf"	"true"	"/reports/qtt_2021.pdf"	"2022-03-31"	"2021-04-01"

"""
txtSchema_financial_results  = """
id: Mã định danh duy nhất của mỗi bản ghi trong bảng financial_results. và là khóa chính của bảng.

total_assets: Tổng tài sản của nhà thầu. Trường này lưu trữ tổng giá trị của tất cả tài sản mà nhà thầu sở hữu tại thời điểm báo cáo tài chính.

total_liabilities: Tổng nợ phải trả của nhà thầu. Trường này lưu trữ tổng giá trị các khoản nợ mà nhà thầu phải thanh toán, bao gồm cả nợ dài hạn và ngắn hạn.

short_term_assets: Tài sản ngắn hạn của nhà thầu. Trường này lưu trữ giá trị của các tài sản có thể chuyển đổi thành tiền mặt trong vòng một năm, ví dụ như tiền mặt, hàng tồn kho, hoặc các khoản phải thu ngắn hạn.

short_term_liabilities: Nợ ngắn hạn của nhà thầu. Trường này lưu trữ các khoản nợ phải trả trong vòng một năm, ví dụ như các khoản vay ngắn hạn hoặc các khoản nợ phải trả khác.

net_asset_value: Giá trị tài sản ròng của nhà thầu. Trường này lưu trữ giá trị tài sản ròng của nhà thầu, được tính bằng tổng tài sản trừ đi tổng nợ phải trả.

working_capital: Vốn lưu động của nhà thầu. Trường này lưu trữ số vốn mà nhà thầu có sẵn để tài trợ cho các hoạt động kinh doanh hàng ngày, được tính bằng tài sản ngắn hạn trừ đi nợ ngắn hạn.

revenue: Doanh thu của nhà thầu. Trường này lưu trữ tổng giá trị thu được từ hoạt động kinh doanh của nhà thầu trong năm tài chính, trước thuế.

profit_before_tax: Lợi nhuận trước thuế của nhà thầu. Trường này lưu trữ lợi nhuận mà nhà thầu có được trước khi tính đến các khoản thuế phải nộp.

profit_after_tax: Lợi nhuận sau thuế của nhà thầu. Trường này lưu trữ lợi nhuận thực tế mà nhà thầu có được sau khi đã trừ thuế thu nhập doanh nghiệp.

has_financial_report: Chỉ số cho biết liệu nhà thầu có báo cáo tài chính hợp lệ hay không. Trường này có kiểu dữ liệu boolean (true/false).

financial_report_url: Đường dẫn tới báo cáo tài chính của nhà thầu. Trường này chứa đường link dẫn tới báo cáo tài chính có sẵn của nhà thầu, ví dụ như file PDF.

has_tax_declaration: Chỉ số cho biết liệu nhà thầu có thực hiện khai thuế trong năm tài chính hay không. Trường này có kiểu dữ liệu boolean (true/false).

tax_declaration_url: Đường dẫn tới tài liệu khai thuế của nhà thầu. Trường này chứa đường link dẫn tới các tài liệu liên quan đến khai thuế của nhà thầu, ví dụ như file PDF.

has_tax_payment: Chỉ số cho biết liệu nhà thầu có thực hiện nộp thuế trong năm tài chính hay không. Trường này có kiểu dữ liệu boolean (true/false).

tax_payment_url: Đường dẫn tới tài liệu chứng minh việc nộp thuế của nhà thầu. Trường này chứa đường link dẫn tới các tài liệu liên quan đến việc nộp thuế, ví dụ như file PDF.

financial_year_to: Ngày kết thúc năm tài chính của nhà thầu. Trường này lưu trữ ngày cuối cùng của năm tài chính mà báo cáo tài chính của nhà thầu đề cập đến.

financial_year_from: Ngày bắt đầu năm tài chính của nhà thầu. Trường này lưu trữ ngày bắt đầu của năm tài chính mà báo cáo tài chính của nhà thầu đề cập đến.
"""

####### Finance Requirements
sqlSchema_finance_requirements = """
CREATE TABLE public.finance_requirement (
	id serial4 NOT NULL,
	proposal_id int2 NULL,
	requirements text NULL,
	description text NULL,
	document_name varchar NULL,
	createdate timestamp NULL DEFAULT now(),
	
	answer text NULL,
	reason text NULL,
	link text NULL,
	compliance_confirmation text NULL,
	CONSTRAINT finance_requirement_pk PRIMARY KEY (id),
	CONSTRAINT finance_requirement_fk FOREIGN KEY (proposal_id) REFERENCES public.proposal(id)
);

Below are 5 sample records:
"id"    "proposal_id"	"requirements"	                "description"	                                "document_name"	                "createdate"	                "answer"	"reason"
2034	678	            "Thực hiện nghĩa vụ thuế"	    "Đã thực hiện nghĩa vụ thuế(4) của năm tài      "Cam kết trong đơn dự thầu"	    "2025-04-02 18:14:09.492"			
                                                        chính gần nhất so với thời điểm đóng thầu."	

2035	678	            "Kết quả hoạt động tài chính"	"Giá trị tài sản ròng của nhà thầu trong        "Mẫu số 08"             	    "2025-04-02 18:14:09.492"		
                                                        năm tài chính gần nhất so với thời điểm đóng 
                                                        thầu phải dương. (Giá trị tài sản ròng = Tổng 
                                                        tài sản - Tổng nợ)"		

2036	678	            "Doanh thu bình quân hằng năm   "Doanh thu bình quân hằng năm (không bao gồm    "Mẫu số 08"	                    "2025-04-02 18:14:09.492"		
                        (không bao gồm thuế VAT)"       thuế VAT) của 3 (6) năm tài chính gần nhất so 
                                                        với thời điểm đóng thầu của nhà thầu có giá trị
                                                        tối thiểu là 2.808.300.000(7)VND.		
"""
# Fetch schema Finance Requirements
txtSchema_finance_requirements = """
Mô tả chi tiết các fields trong bảng finace_requirement:
id: Mã định danh duy nhất của mỗi yêu cầu tài chính. Trường này được tạo tự động (serial4), và là khóa chính của bảng.

proposal_id: Mã định danh của hồ sơ mời thầu (proposal). Trường này là khóa ngoại, liên kết với trường id trong bảng proposal, giúp xác định yêu cầu tài chính này thuộc về hồ sơ mời thầu nào.

requirements: Yêu cầu tài chính mà nhà thầu cần phải đáp ứng. Trường này mô tả các yêu cầu hoặc tiêu chí về tài chính mà nhà thầu cần phải cung cấp trong hồ sơ thầu, ví dụ như mức doanh thu, lợi nhuận hoặc các yêu cầu tài chính khác.

description: Mô tả chi tiết về yêu cầu tài chính. Trường này cung cấp thông tin chi tiết về yêu cầu tài chính, giải thích rõ hơn về mục tiêu, tiêu chí và các điều kiện liên quan đến yêu cầu tài chính đó.

document_name: Tên tài liệu chứng minh yêu cầu tài chính. Trường này lưu trữ tên tài liệu hoặc bản sao các tài liệu mà nhà thầu cần cung cấp để chứng minh đã đáp ứng yêu cầu tài chính, ví dụ như báo cáo tài chính, hợp đồng, giấy chứng nhận.

createdate: Thời gian tạo yêu cầu tài chính. Trường này lưu trữ thời điểm mà yêu cầu tài chính được tạo ra trong hệ thống, được tự động gán giá trị khi bản ghi được tạo.

answer: Câu trả lời của nhà thầu đối với câu hỏi về yêu cầu tài chính. Trường này lưu trữ câu trả lời của nhà thầu đối với câu hỏi trong trường question, ví dụ như "Doanh thu trung bình hàng năm là 50 tỷ VND."

reason: Lý do hoặc giải thích cho câu trả lời. Trường này lưu trữ các lý do hoặc giải thích mà nhà thầu cung cấp để chứng minh hoặc làm rõ câu trả lời cho yêu cầu tài chính.

link: Đường dẫn tới tài liệu hoặc nguồn thông tin hỗ trợ yêu cầu tài chính. Trường này chứa URL của các tài liệu, chứng từ hoặc các nguồn thông tin trực tuyến mà nhà thầu cung cấp để chứng minh đã đáp ứng yêu cầu tài chính.

compliance_confirmation: Xác nhận sự tuân thủ yêu cầu tài chính. Trường này lưu trữ thông tin về việc nhà thầu đã xác nhận hoặc cam kết tuân thủ các yêu cầu tài chính, có thể là "Đã tuân thủ" hoặc "Chưa tuân thủ".
""" 

# Fetch schema info
sqlSample = """
requirements: "Đã thực hiện nghĩa vụ kê khai thuế, nộp thuế của năm tài chính gần nhất so với thời điểm đóng thầu."
sql:
WITH latest_financial_year AS (
    SELECT 
        id,
        financial_year_from,
        financial_year_to,
        has_tax_declaration,
        tax_declaration_url,
        has_tax_payment,
        tax_payment_url
    FROM 
        public.financial_results
    WHERE 
        financial_year_to <= '2024-03-28'
    ORDER BY 
        financial_year_to DESC
    LIMIT 1
)
SELECT 
    lfy.id,
    lfy.financial_year_from,
    lfy.financial_year_to,
    lfy.has_tax_declaration,
    lfy.tax_declaration_url,
    lfy.has_tax_payment,
    lfy.tax_payment_url,
    CASE
        WHEN lfy.has_tax_declaration = true AND lfy.has_tax_payment = true THEN 
            'Đã kê khai và nộp thuế'
        WHEN lfy.has_tax_declaration = true AND lfy.has_tax_payment = false THEN 
            'Đã kê khai nhưng chưa nộp thuế'
        WHEN lfy.has_tax_declaration = false AND lfy.has_tax_payment = true THEN 
            'Chỉ nộp thuế nhưng chưa kê khai'
        WHEN lfy.has_tax_declaration = false AND lfy.has_tax_payment = false THEN 
            'Chưa kê khai và chưa nộp thuế'
        ELSE 
            'Thiếu thông tin về kê khai/nộp thuế'
    END AS tax_status
FROM 
    latest_financial_year lfy;
"""
sqlSample = """
requirements: "Đã thực hiện nghĩa vụ kê khai thuế của năm tài chính gần nhất so với thời điểm đóng thầu."
sql:
WITH latest_financial_year AS (
    SELECT 
        id,
        financial_year_from,
        financial_year_to,
        has_tax_payment,
        tax_payment_url
    FROM 
        public.financial_results
    WHERE 
        financial_year_to <= '2024-03-28'
    ORDER BY 
        financial_year_to DESC
    LIMIT 1
)
SELECT 
    lfy.id,
    lfy.financial_year_from,
    lfy.financial_year_to,
    lfy.has_tax_payment,
    lfy.tax_payment_url,
    CASE
        WHEN lfy.has_tax_payment = true 
            'Đã kê khai thuế'
        WHEN lfy.has_tax_payment = false
            'Chưa kê khai thuế'
        ELSE 
            'Thiếu thông tin về kê khai thuế'
    END AS tax_status
FROM 
    latest_financial_year lfy;
"""
sqlSample = """
requirements: "Đã thực hiện nghĩa nộp thuế của năm tài chính gần nhất so với thời điểm đóng thầu."
sql:
WITH latest_financial_year AS (
    SELECT 
        id,
        financial_year_from,
        financial_year_to,
        has_tax_declaration,
        tax_declaration_url
    FROM 
        public.financial_results
    WHERE 
        financial_year_to <= '2024-03-28'
    ORDER BY 
        financial_year_to DESC
    LIMIT 1
)
SELECT 
    lfy.id,
    lfy.financial_year_from,
    lfy.financial_year_to,
    lfy.has_tax_declaration,
    lfy.tax_declaration_url,
    CASE
        WHEN lfy.has_tax_declaration = true 
            'Đã nộp thuế'
        WHEN lfy.has_tax_declaration = false
            'Chưa nộp thuế'
        ELSE 
            'Thiếu thông tin về nộp thuế'
    END AS tax_status
FROM 
    latest_financial_year lfy;
"""

sqlSample2 = """
requirements: "Doanh thu bình quân hằng năm (không bao gồm thuế VAT) của 3 năm tài chính gần nhất so với thời điểm đóng thầu của nhà thầu có giá trị tối thiểu là 10.906.916.100(9) VND."
sql:
WITH latest_results AS (
    SELECT 
        id, 
        revenue, 
        financial_report_url
    FROM 
        public.financial_results
    WHERE 
        financial_year_to <= '2024-03-28'
    ORDER BY 
        financial_year_to DESC
    LIMIT 3
),
avg_result AS (
    SELECT AVG(revenue) AS avg_revenue FROM latest_results
)
SELECT 
    lr.*, 
    ar.avg_revenue
FROM 
    latest_results lr,
    avg_result ar
WHERE 
    ar.avg_revenue >= 17385000000;
"""
sqlSample3 = """
requirements: "Giá trị tài sản ròng của nhà thầu trong năm tài chính gần nhất so với thời điểm đóng thầu phải dương. (Giá trị tài sản ròng = Tổng tài sản - Tổng nợ)"
sql:
SELECT id, net_asset_value,financial_report_url
FROM public.financial_results
WHERE financial_year_to <= '2025-01-07'
  AND net_asset_value > 0
ORDER BY financial_year_to DESC
LIMIT 1;
"""

sql_expert_system_prompt = f"""
As an SQL Expert, you are a critical member of our data team, responsible for designing, optimizing, and maintaining our database systems. Your expertise in SQL and database management ensures that our data is accurate, accessible, and efficiently processed.

Your goal is to develop and optimize complex SQL queries to answer the question.

You are given the following schema:
{sqlSchema_finance_requirements}
{sqlSchema_financial_results}

Description for schema:
{txtSchema_finance_requirements}
{txtSchema_financial_results}

Sample:
{sqlSample}
{sqlSample2}
{sqlSample3}

Your task is to use the provided schema, and produce the SQL query needed to answer user question. Collaborate with SQL Executor for feedback and review, ensuring that your SQL solutions is correct and follow best practices in database design and query optimization to enhance performance and reliability.
The output should be a an optimized SQL query. Ensure that your output only contains SQL query, nothing else.

Trả về kết quả dưới dạng JSON với cấu trúc:
    "sql_query": [
        {{
            "finance_requirement_id": id ,
            "question": "Câu hỏi tự động được viết",
            "sql": "Câu lệnh sql được tạo từ question viết thành một dòng dạng str"
        }},...
    ]
    ví dụ:
"""

sql_expert_system_prompt_v1_0_1 = f"""
As an SQL Expert, you are a critical member of our data team, responsible for designing, optimizing, and maintaining our database systems. Your expertise in SQL and database management ensures that our data is accurate, accessible, and efficiently processed.

Your goal is to develop and optimize complex SQL queries to answer the requirement.

You are given the following schema:
{sqlSchema_finance_requirements}
{sqlSchema_financial_results}

Description for schema:
{txtSchema_finance_requirements}
{txtSchema_financial_results}

Sample:
{sqlSample}
{sqlSample2}
{sqlSample3}

Your task is to use the provided schema, requirements, and descriptions to create the SQL query needed to answer the user's request.
Work with SQL Executor for feedback and review, ensuring that your SQL solutions are correct and follow best practices in database design and query optimization for performance and reliability.
The output should be an optimized SQL query.KHÔNG lấy dữ liệu trong() ví dụ (7),(6) khi đọc mô tả và yêu cầu,
Đối với các số tiền phải giữ nguyên đúng số và số lượng các số trong số tiền cần lấy khi cho vào câu lệnh sql.
ví dụ: 2.808.300.000.000 VND thì bóc thành 2808300000000
Make sure your output contains only the SQL query, nothing else.
QUAN TRỌNG - HƯỚNG DẪN SO SÁNH SỐ HỌC:
    1. Khi so sánh các giá trị tiền tệ, hãy chuyển tất cả giá trị về cùng một đơn vị (VND).
    2. Dấu chấm (.) là phần phần nghìn và dấu phẩy (,) là phần thập phân
    3. Chú ý đến số lượng chữ số:
    ví dụ:
       - 1.000.000.000 đọc là 1 tỷ 
       - 1.000.000 đọc là 1 triệu
       - 1.200.000.000.000 đọc là 1.2 nghìn tỷ 
       - 2.800.000.000 đọc là 2.8 tỷ
       - 2.800.000.000.000 đọc là 2.8 nghìn tỷ 
    4. Đếm số chữ số và thêm các số không cần thiết để so sánh chính xác.
Trả về kết quả dưới dạng JSON với cấu trúc:
    "sql_query": [
        {{
            "finance_requirement_id": finance_requirement_id,
            "sql": "Câu lệnh sql được tạo từ yêu cầu viết thành một dòng dạng str"
        }},...
    ]

"""

class SQLExpertNodeV1:
    """SQL Expert Node V1"""

    def __init__(self, name: str, llm: ChatOpenAI, prompt: str = sql_expert_system_prompt):
        self.name = name
        self.llm = llm
        self.prompt = prompt

    # Defining __call__ method
    def __call__(self, state: StateSqlFinance):
        print(f"Executing node: {self.name}")
        
        # Lấy tất cả câu hỏi từ messages (lọc HumanMessage)
        questions = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)]
        
        # Tạo tin nhắn cho LLM
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "human", "content": "\n".join(questions)}
        ]
        
        # Gọi LLM để tạo danh sách SQL
        result = self.llm.with_structured_output(None, method="json_mode").invoke(messages)
        # Trích xuất các câu lệnh SQL từ danh sách dictionary
        # Trích xuất danh sách sql_query từ result
        sql_query_list = result["sql_query"]  # Expecting a list of dicts like [{"finance_requirement_id": ..., "question": ..., "sql": ...}, ...]
        
        # Chuyển đổi thành JSON string để lưu vào HumanMessage
        sql_queries_json = json.dumps({"sql_query": sql_query_list}, ensure_ascii=False)
        print(f"[{self.name}] RESULT: {sql_queries_json}")
        
        # Trả về câu lệnh SQL trong messages
        return {
            "messages": state["messages"] + [HumanMessage(content=sql_queries_json, name=self.name)]
        }

class SQLExpertNodeV1m0p1:
    """SQL Expert Node V1.0.1"""

    def __init__(self, name: str, llm: ChatOpenAI, prompt: str = sql_expert_system_prompt_v1_0_1):
        self.name = name
        self.llm = llm
        self.prompt = prompt

    # Defining __call__ method
    def __call__(self, state: StateSqlFinance):
        print(f"Executing node: {self.name}")
        
        # Lấy tất cả câu hỏi từ messages (lọc HumanMessage)
        questions = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)]
        
        # Tạo tin nhắn cho LLM
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "human", "content": "\n".join(questions)}
        ]
        
        # Gọi LLM để tạo danh sách SQL
        result = self.llm.with_structured_output(None, method="json_mode").invoke(messages)
        # Trích xuất các câu lệnh SQL từ danh sách dictionary
        # Trích xuất danh sách sql_query từ result
        sql_query_list = result["sql_query"]  # Expecting a list of dicts like [{"finance_requirement_id": ..., "question": ..., "sql": ...}, ...]
        
        # Chuyển đổi thành JSON string để lưu vào HumanMessage
        sql_queries_json = json.dumps({"sql_query": sql_query_list}, ensure_ascii=False)
        print(f"[{self.name}] RESULT: {sql_queries_json}")
        
        # Trả về câu lệnh SQL trong messages
        return {
            "messages": state["messages"] + [HumanMessage(content=sql_queries_json, name=self.name)]
        }
