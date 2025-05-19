# Standard imports
import time
from datetime import datetime
from typing import Any, Dict

# Third party imports
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Your imports
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.storage import pgdb_proposal
from app.model_ai import llm
from app.utils.logger import get_logger 
from app.utils.insert_technical import insert_technical

logger = get_logger("except_handling_extraction")

class PostExtractionMDNodeV2m0p0:
    """
    PostExtractionMDNodeV2m0p0
    Xử lý các bước sau khi các quá trình bóc tách dữ liệu hoàn thành hết.
    - Input: result_extraction_hr: Any
             result_extraction_finance: List[ExtractFinanceRequirement]
             result_extraction_experience: List[ExtractExperienceRequirement]
             result_extraction_overview: ExtractOverviewBiddingDocuments
    - Output: status: str - OK / NOK
              update to db
    """

    def __init__(self, name: str):
        self.name = name

    def check_format_date(self, date: str, format: str = "%d/%m/%Y"):
        """
        Check and format date to 'YYYY-MM-DD' format
        """
        possible_formats = [
            "%d/%m/%Y %H:%M",  # 28/03/2024 09:00
            "%d/%m/%Y",  # 28/03/2024
            "%Y-%m-%d %H:%M:%S",  # 2024-03-28 09:00:00
            "%Y-%m-%d",  # 2024-03-28
        ]
        for fmt in possible_formats:
            try:
                date_object = datetime.strptime(date, fmt)
                formatted_date = date_object.strftime("%Y-%m-%d")
                return f"'{formatted_date}'"
            except ValueError:
                continue
        return "NULL"  # Nếu không khớp bất kỳ format nào
    
    def merge_hr_requirements(self, result_extraction_hr: Dict[str, Any], result_extraction_technology: Dict[str, Any]):
        """
            merge_hr_requirements
            Gộp và so sánh yêu cầu nhân sự từ 2 JSON HR.
            Args:
                - result_extraction_hr: Dict[str, Any] - JSON A (Hồ sơ mời thầu HR)
                - result_extraction_technology: Dict[str, Any] - JSON B (Yêu cầu kỹ thuật HR)
            Output:
                - result: Dict[str, Any] - Kết quả gộp và so sánh yêu cầu nhân sự
        """
        llm_structured = llm.chat_model_gpt_4o_mini().with_structured_output(None, method="json_mode")
        system_prompt_template = PromptTemplate.from_template(
        """
            Bạn là một chuyên gia phân tích và so sánh dữ liệu đầu vào.
            Dưới đây là hai JSON chứa yêu cầu nhân sự (HR) cho các vị trí khác nhau.Hãy phân tích và xác định các yêu cầu nhân sự từ hai JSON này. 
            **Yêu cầu xử lý:**
                + Nếu một vị trí chỉ có trong một JSON, hãy giữ nguyên vị trí đó và gộp chúng lại.
                + Nếu có sự trùng lặp giữa hai JSON:
                    - So sánh chi tiết từng trường: yêu cầu bằng cấp, số lượng, kinh nghiệm, chứng chỉ, v.v.
                    - Ưu tiên giữ lại thông tin chi tiết hơn, đầy đủ hơn hoặc hợp lý hơn giữa hai nguồn.
                    - Nếu thông tin từ cả hai nguồn đều hữu ích, hãy gộp lại có cấu trúc.
            
            **Ví dụ:**
            *Ví dụ 1: Trùng yêu cầu và mô tả:
                INPUT:
                    JSON A: "result_extraction_hr": {{"hr": [{{"position": "Kỹ sư mạng","quantity": "2","requirements": [{{"name": "Bằng cấp","description": "Tốt nghiệp đại học ngành CNTT."}}]}}]}},
                    JSON B: "result_extraction_technology": {{"hr": [{{"position": "Kỹ sư mạng","quantity": "2","requirements": [{{"name": "Bằng cấp","description": "Tốt nghiệp đại học ngành CNTT."}}]}}]}}
                OUTPUT:
                    {{"hr": [{{"position": "Kỹ sư mạng","quantity": "2","requirements": [{{"name": "Bằng cấp","description": "Tốt nghiệp đại học ngành CNTT."}}]}}]}}

            *Ví dụ 2: Trùng tên yêu cầu, mô tả khác:
                INPUT:
                    JSON A: "result_extraction_hr": {{"hr": [{{"position": "Lập trình viên","quantity": "3","requirements": [{{"name": "Kinh nghiệm","description": "Ít nhất 2 năm kinh nghiệm phát triển phần mềm."}}]}}]}},
                    JSON B: "result_extraction_technology": {{"hr": [{{"position": "Lập trình viên","quantity": "3","requirements": [{{"name": "Kinh nghiệm","description": "Đã từng tham gia phát triển hệ thống lớn sử dụng Python hoặc Java."}}]}}]}}
                OUTPUT:
                    {{"hr": [{{"position": "Lập trình viên","quantity": "3","requirements": [{{"name": "Kinh nghiệm","description": "• Ít nhất 2 năm kinh nghiệm phát triển phần mềm.\n• Đã từng tham gia phát triển hệ thống lớn sử dụng Python hoặc Java."}}]}}]}}
                
            *Ví dụ 3: Yêu cầu khác biệt:
                INPUT:
                    JSON A: "result_extraction_hr": {{"hr": [{{"position": "Quản trị hệ thống","quantity": "1","requirements": [{{"name": "Chứng chỉ","description": "Có chứng chỉ MCSA hoặc tương đương."}}]}}]}},
                    JSON B: "result_extraction_technology": {{"hr": [{{"position": "Quản trị hệ thống","quantity": "1","requirements": [{{"name": "Trình độ chuyên môn","description": "Tốt nghiệp đại học chuyên ngành Hệ thống thông tin."}}]}}]}}
                OUTPUT:
                    {{"hr": [{{"position": "Quản trị hệ thống","quantity": "1","requirements"{{"name": "Chứng chỉ","description": "Có chứng chỉ MCSA hoặc tương đươn{{"name": "Trình độ chuyên môn","description": "Tốt nghiệp đại học chuyên ngành Hệ thống thông ti}}]}}]}}
                    
            **Đầu vào:
                JSON A (Hồ sơ mời thầu HR):
                {result_extraction_hr}

                JSON B (Yêu cầu kỹ thuật HR):
                {result_extraction_technology}
            Kết luận: (Hãy đưa ra kết quả cuối cùng dựa trên phân tích của bạn)
        """)
        merge_chain = system_prompt_template | llm_structured
        result = merge_chain.invoke({
            "result_extraction_hr": result_extraction_hr,
            "result_extraction_technology": result_extraction_technology,
        })
        return result["hr"] if "hr" in result else []

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        try:
            start_time = time.perf_counter()
            # 1. insert into proposal table
            is_data_extracted_finance = False
            proposal_overview = state.get("result_extraction_overview")
            proposal_notice_bid = state.get("result_extraction_notice_bid", {})
            proposal_summary_hsmt = state.get("summary_hsmt", "")
            result_extraction_finance = state.get("result_extraction_finance", [])
            # date_object = datetime.strptime(proposal_overview.release_date, "%d/%m/%Y")
            # formatted_date = date_object.strftime("%Y-%m-%d")
            # Kiểm tra xem tài chính sau khi bóc tách có dữ liệu không
            if len(result_extraction_finance) > 0:
                is_data_extracted_finance = True
            # Đảm bảo proposal_notice_bid là dict (nếu là list, lấy phần tử đầu tiên)
            if isinstance(proposal_notice_bid, list) and proposal_notice_bid:
                proposal_notice_bid = proposal_notice_bid[0]
            if not isinstance(proposal_notice_bid, dict):  # Nếu vẫn không phải dict, đặt thành {}
                proposal_notice_bid = {}
            print(proposal_overview.get("release_date", None))
            formatted_date = (
                self.check_format_date(proposal_overview.get("release_date", None))
                if proposal_overview and proposal_overview.get("release_date", None)
                else "NULL"
            )
            print(formatted_date)
            closing_time = (
                self.check_format_date(proposal_notice_bid["bid_closing_time"])
                if proposal_notice_bid and "bid_closing_time" in proposal_notice_bid
                else "NULL"
            )
            proposal_info = pgdb_proposal.ProposalV1_0_3(
                investor_name=proposal_overview.get("investor_name", None),
                proposal_name=proposal_overview.get("proposal_name", None),
                release_date=formatted_date,
                project=proposal_overview.get("project", None),
                package_number=proposal_overview.get("package_number", None),
                decision_number=proposal_overview.get("decision_number", None),
                agentai_name=state["agentai_name"],
                agentai_code=state["agentai_code"],
                filename="Ho_so_moi_thau.pdf",
                status="EXTRACTED",
                email_content_id=state["email_content_id"],

                selection_method=proposal_notice_bid.get("contractor_selection_method",""),
                field=proposal_notice_bid.get("field",""),
                execution_duration=proposal_notice_bid.get("package_execution_time",""),
                closing_time=closing_time,
                validity_period=proposal_notice_bid.get("bid_validity",""),
                security_amount=proposal_notice_bid.get("bid_security_amount",""),
                summary=proposal_summary_hsmt,

            )

            proposal_id = pgdb_proposal.insert_proposal_v1_0_3(proposal_info)
            print("inserted proposal overivew")
            # sql = "UPDATE proposal SET email_content_id = %s WHERE id=%s"
            # params = (state["email_content_id"], proposal_id)
            # executeSQL(sql, params)
            # 2. insert into finance_requirement table
            # list of finance_requirement to be inserted
            finance_requirements = [
                pgdb_proposal.FinanceRequirement(
                    proposal_id=proposal_id,
                    requirements=fr.requirement,
                    description=fr.description,
                    document_name=fr.document_name,
                )
                for fr in state["result_extraction_finance"]
            ]

            pgdb_proposal.insert_many_finance_requirement(finance_requirements)
            print("inserted finance requirement")
            # 3. insert into hr requirement and hr detail requirement table
            result_extraction_hr = state.get("result_extraction_hr", [])
            result_extraction_technology = state.get("result_extraction_technology", {})
            if isinstance(result_extraction_technology, dict):
                hr_items = result_extraction_technology.get("hr", [])
                if isinstance(hr_items, list) and len(hr_items) > 0:
                    result_extraction_hr = self.merge_hr_requirements(result_extraction_hr, hr_items)
            pgdb_proposal.insert_many_hr_requirement(
                proposal_id, result_extraction_hr
            )
            print("inserted hr requirement")
            # 4. insert into experience requirement table
            # list of experience_requirement to be inserted
            experience_requirements = [
                pgdb_proposal.ExperienceRequirement(
                    proposal_id=proposal_id,
                    requirements=fr.requirement,
                    description=fr.description,
                    document_name=fr.document_name,
                )
                for fr in state["result_extraction_experience"]
            ]
            pgdb_proposal.insert_many_experience_requirement(experience_requirements)
            print("inserted experience requirement")

            # 5. insert technology
            if len(result_extraction_technology) > 0:
                insert_technical(result_extraction_technology, proposal_id)
                print("inserted technology requirement")

            error_messages = state.get("error_messages", [])
            if len(error_messages) > 0:
                # Log the error messages
                for msg in error_messages:
                    logger.error(msg)
            finish_time = time.perf_counter()

            print(f"Total time: {finish_time - start_time} s")
            return {
                "proposal_id": proposal_id,
                "is_data_extracted_finance": is_data_extracted_finance
            }
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}", 
                include_trace=True
            )
            return {
                "result_extraction_technology": [],
                "error_messages": [error_msg],
            }