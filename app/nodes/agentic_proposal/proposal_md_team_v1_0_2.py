# Standard imports
import time

# Third party imports
from langgraph.graph import StateGraph, START, END

# Your imports
from app.nodes.agentic_proposal.classify_document_pdf import ClassifyDocumentPdfNodeV1
from app.nodes.states.state_proposal_v1 import StateProposalV1

from app.nodes.agentic_proposal.chapter_content_node import ChapterContentMDNodeV1
from app.nodes.agentic_proposal.extraction_overview_node import ExtractionOverviewMDNodeV1
from app.nodes.agentic_proposal.extraction_hr_node import ExtractionHRMDNodeV1m1p0
from app.nodes.agentic_proposal.extraction_finance_node import ExtractionFinanceMDNodeV1m0p1
from app.nodes.agentic_proposal.extraction_experience_node import ExtractionExperienceMDNodeV1m0p0
from app.nodes.agentic_proposal.post_extraction_node import PostExtractionMDNodeV1
from app.nodes.agentic_proposal.generate_excel_reply_email import GenerateExcelReplyEmailNodeV1

def proposal_md_team_graph_v1_0_2():
    """proposal_team_graph_v1_0_2"""
    start_time = time.perf_counter()

    #
    # Define Node
    #
    # 1. Classify Document PDF
    classify_document_pdf_node_v1 = ClassifyDocumentPdfNodeV1(
        name="ClassifyDocumentPdfNodeV1",
    )
    # 8. Extraction Overview MD
    extraction_overview_md_node_v1 = ExtractionOverviewMDNodeV1(
        name="ExtractionOverviewMDNodeV1",
    )
    # 9. Extraction HR MD
    extraction_hr_md_node_v1 = ExtractionHRMDNodeV1m1p0(
        name="ExtractionHRMDNodeV1m1p0",
    )
    # 10. Extraction Finance MD
    extraction_finance_md_node_v1 = ExtractionFinanceMDNodeV1m0p1(
        name="ExtractionFinanceMDNodeV1m0p1",
    )
    # 11. Extraction Experience MD
    extraction_experience_md_node_v1 = ExtractionExperienceMDNodeV1m0p0(
        name="ExtractionExperienceMDNodeV1m0p0",
    )
    # 12. Post-Extraction MD
    post_extraction_md_node_v1 = PostExtractionMDNodeV1(
        name="PostExtractionMDNodeV1",
    )
    # 13. Generate Excel Reply Email
    generate_excel_reply_email_node_v1= GenerateExcelReplyEmailNodeV1(
        name="GenerateExcelReplyEmailNodeV1"
    )
    #
    # End Define Node
    #
    #
    # Build Graph
    #
    builder = StateGraph(StateProposalV1)
    #
    # Add node
    #
    builder.add_node(classify_document_pdf_node_v1.name, classify_document_pdf_node_v1)
    # 8. Extraction Overview MD
    builder.add_node(extraction_overview_md_node_v1.name, extraction_overview_md_node_v1)
    # 9. Extraction HR MD
    builder.add_node(extraction_hr_md_node_v1.name, extraction_hr_md_node_v1)
    # 10. Extraction Finance MD
    builder.add_node(extraction_finance_md_node_v1.name, extraction_finance_md_node_v1)
    # 11. Extraction Experience MD
    builder.add_node(extraction_experience_md_node_v1.name, extraction_experience_md_node_v1)
    # 12. Post-Extraction MD
    builder.add_node(post_extraction_md_node_v1.name, post_extraction_md_node_v1)
    # 13. Generate Excel Reply Email
    builder.add_node(generate_excel_reply_email_node_v1.name, generate_excel_reply_email_node_v1)
    # ------------
    # End Add Node
    #
    #
    # Create edge
    #
    builder.add_edge(START, classify_document_pdf_node_v1.name)
    builder.add_edge(classify_document_pdf_node_v1.name, extraction_overview_md_node_v1.name)
    # from Extraction Overview MD to Extraction HR MD
    builder.add_edge(extraction_overview_md_node_v1.name, extraction_hr_md_node_v1.name)
    # 8->10
    # from Extraction Overview MD to Extraction Finance MD
    builder.add_edge(extraction_overview_md_node_v1.name, extraction_finance_md_node_v1.name)
    # 8->11
    # from Extraction Overview MD to Extraction Experience MD
    builder.add_edge(extraction_overview_md_node_v1.name, extraction_experience_md_node_v1.name)
    # 9->12
    # from Extraction HR MD to Post-Extraction MD
    builder.add_edge(extraction_hr_md_node_v1.name, post_extraction_md_node_v1.name)
    # 10->12
    # from Extraction Finance MD to Post-Extraction MD
    builder.add_edge(extraction_finance_md_node_v1.name, post_extraction_md_node_v1.name)
    # 11->12
    # from Extraction Experience MD to Post-Extraction MD
    builder.add_edge(extraction_experience_md_node_v1.name, post_extraction_md_node_v1.name)
    # 12-> 13
    # from Post-Extraction to Generate Excel Reply Email
    builder.add_edge(post_extraction_md_node_v1.name, generate_excel_reply_email_node_v1.name)
    # 13-> END
    # from Post-Extraction to END
    builder.add_edge(generate_excel_reply_email_node_v1.name, END)
    # Compile graph
    #
    graph = builder.compile(debug=False)
    finish_time = time.perf_counter()
    print(f"Total time build graph proposal_md_team_graph_v1_0_2 = {finish_time - start_time} s")
    return graph

print("[PROPOSAL_MD_TEAM_GRAPH_V1_0_2]    BUILDING... ")
proposal_md_team_graph_v1_0_2_instance = proposal_md_team_graph_v1_0_2()