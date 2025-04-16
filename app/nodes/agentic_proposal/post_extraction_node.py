# Standard imports
import time
from datetime import datetime

# Third party imports


# Your imports
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.storage import pgdb_proposal
from app.storage.postgre import executeSQL
from app.utils.insert_technical import insert_technical


class PostExtractionMDNodeV1:
    """
    PostExtractionMDNodeV1
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
                return "NULL"

        return "NULL"  # Nếu không khớp bất kỳ format nào
    
    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
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

        formatted_date = (
            self.check_format_date(proposal_overview.release_date)
            if proposal_overview and proposal_overview.release_date
            else "NULL"
        )
        closing_time = (
            self.check_format_date(proposal_notice_bid["bid_closing_time"])
            if proposal_notice_bid and "bid_closing_time" in proposal_notice_bid
            else "NULL"
        )
        proposal_info = pgdb_proposal.ProposalV1_0_3(
            investor_name=proposal_overview.investor_name,
            proposal_name=proposal_overview.proposal_name,
            release_date=formatted_date,
            project=proposal_overview.project,
            package_number=proposal_overview.package_number,
            decision_number=proposal_overview.decision_number,
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
        pgdb_proposal.insert_many_hr_requirement(
            proposal_id, state["result_extraction_hr"]
        )
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
        if len(state["result_extraction_technology"]) > 0:
            insert_technical(state["result_extraction_technology"], proposal_id)
            print("inserted technology requirement")

        print("proposal_id: ", proposal_id)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "proposal_id": proposal_id,
            "is_data_extracted_finance": is_data_extracted_finance
        }
