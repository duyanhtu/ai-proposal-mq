# Standard imports
import time
from datetime import datetime

# Third party imports


# Your imports
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.storage import pgdb_proposal
from app.storage.postgre import executeSQL

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
        try:
            date_object = datetime.strptime(date, format)
            formatted_date = date_object.strftime("%Y-%m-%d")
            return f"'{formatted_date}'"
        except ValueError:
            return "NULL"

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        # 1. insert into proposal table
        proposal_overview = state["result_extraction_overview"]

        # date_object = datetime.strptime(proposal_overview.release_date, "%d/%m/%Y")
        # formatted_date = date_object.strftime("%Y-%m-%d")
        formatted_date = self.check_format_date(proposal_overview.release_date)
        proposal_info = pgdb_proposal.ProposalV1_0_2(
            investor_name=proposal_overview.investor_name,
            proposal_name=proposal_overview.proposal_name,
            # release_date=formatted_date,
            release_date=formatted_date,
            project=proposal_overview.project,
            package_number=proposal_overview.package_number,
            decision_number=proposal_overview.decision_number,
            agentai_name=state["agentai_name"],
            agentai_code=state["agentai_code"],
            # filename=state["filename"],
            filename="Ho_so_moi_thau.pdf",
            status="EXTRACTED",
            email_content_id=state["email_content_id"]
        )

        proposal_id = pgdb_proposal.insert_proposal_v1_0_2(proposal_info)
        print("inserted proposal overivew")
        sql = "UPDATE proposal SET email_content_id = %s WHERE id=%s"
        params = (state['email_content_id'],proposal_id)
        executeSQL(sql, params)
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
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {"proposal_id": proposal_id}