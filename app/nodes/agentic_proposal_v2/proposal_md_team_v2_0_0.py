# Standard imports
import time

# Third party imports
from langgraph.graph import StateGraph, START, END

# Your imports
from app.nodes.states.state_proposal_v1 import StateProposalV1

from app.nodes.agentic_proposal_v2.classify_document_pdf import ClassifyDocumentPdfNodeV2m0p0
from app.nodes.agentic_proposal_v2.extraction_hr_node import ExtractionHRMDNodeV2m0p0
from app.nodes.agentic_proposal_v2.extraction_finance_node import ExtractionFinanceMDNodeV2m0p0
from app.nodes.agentic_proposal_v2.extraction_experience_node import ExtractionExperienceMDNodeV2m0p0
from app.nodes.agentic_proposal_v2.extraction_technology_node import ExtractionTechnologyNodeV2m0p0
from app.nodes.agentic_proposal_v2.post_extraction_node import PostExtractionMDNodeV2m0p0
from app.nodes.agentic_proposal_v2.prepare_data_document import PrepareDataDocumentNodeV2m0p0
from app.nodes.agentic_proposal_v2.extraction_notice_bid_node import ExtractionNoticeBidMDNodeV2m0p0
from app.nodes.agentic_proposal_v2.summary_hsmt_node import SummaryHSMTNodeV2m0p0
def proposal_md_team_graph_v2_0_0():
    """proposal_md_team_graph_v2_0_0"""
    start_time = time.perf_counter()

    #
    # Define Node
    #
    prepare_data_document_node_v2 = PrepareDataDocumentNodeV2m0p0(
        name="PrepareDataDocumentNodeV2m0p0",
    )
    # 1. Classify Document PDF
    classify_document_pdf_node_v2 = ClassifyDocumentPdfNodeV2m0p0(
        name="ClassifyDocumentPdfNodeV2m0p0",
    )
    # 9. Extraction HR MD
    extraction_hr_md_node_v2 = ExtractionHRMDNodeV2m0p0(
        name="ExtractionHRMDNodeV2m0p0",
    )
    # 10. Extraction Finance MD
    extraction_finance_md_node_v2 = ExtractionFinanceMDNodeV2m0p0(
        name="ExtractionFinanceMDNodeV2m0p0",
    )
    # 11. Extraction Experience MD
    extraction_experience_md_node_v2 = ExtractionExperienceMDNodeV2m0p0(
        name="ExtractionExperienceMDNodeV2m0p0",
    )
    # ?. Extraction Technology MD
    extraction_technology_md_node_v2 = ExtractionTechnologyNodeV2m0p0(
        name="ExtractionTechnologyNodeV2m0p0", 
    )
    # ?. Extraction Notice Bid MD
    extraction_notice_bid_md_node_v2 = ExtractionNoticeBidMDNodeV2m0p0(
        name="ExtractionNoticeBidMDNodeV2m0p0",
    )
    # ?. Summary HSMT 
    summary_hsmt_node_v2 = SummaryHSMTNodeV2m0p0(
        name="SummaryHSMTNodeV2m0p0",
    )
    # 12. Post-Extraction MD
    post_extraction_md_node_v2 = PostExtractionMDNodeV2m0p0(
        name="PostExtractionMDNodeV2m0p0",
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
    # ?. Prepare Data MD
    builder.add_node(prepare_data_document_node_v2.name, prepare_data_document_node_v2)
    #
    builder.add_node(classify_document_pdf_node_v2.name, classify_document_pdf_node_v2)
   # 9. Extraction HR MD
    builder.add_node(extraction_hr_md_node_v2.name, extraction_hr_md_node_v2)
    # 10. Extraction Finance MD
    builder.add_node(extraction_finance_md_node_v2.name, extraction_finance_md_node_v2)
    # 11. Extraction Experience MD
    builder.add_node(extraction_experience_md_node_v2.name, extraction_experience_md_node_v2)
    # ?. Extraction Technology MD
    builder.add_node(extraction_technology_md_node_v2.name, extraction_technology_md_node_v2)
    # ?. Extraction Notice Bid MD
    builder.add_node(extraction_notice_bid_md_node_v2.name, extraction_notice_bid_md_node_v2)
    # ?. Summary HSMT
    builder.add_node(summary_hsmt_node_v2.name, summary_hsmt_node_v2)
    # 12. Post-Extraction MD
    builder.add_node(post_extraction_md_node_v2.name, post_extraction_md_node_v2)
    # # 13. Generate Excel And Docx
    # builder.add_node(generate_excel_and_docx_node_v1.name, generate_excel_and_docx_node_v1)
    # ------------
    # End Add Node
    #
    #
    # Create edge
    #
    # ?. from START to Prepare Data Document
    builder.add_edge(START, prepare_data_document_node_v2.name)
    # ?. from Prepare Data Document to Classify Document PDF
    builder.add_edge(prepare_data_document_node_v2.name, classify_document_pdf_node_v2.name)
    # ?. from Classify Document PDF to Extraction Overview MD
    builder.add_edge(classify_document_pdf_node_v2.name, summary_hsmt_node_v2.name)
    # from Extraction Overview MD to Extraction HR MD
    builder.add_edge(summary_hsmt_node_v2.name, extraction_hr_md_node_v2.name)
    # 8->10
    # from Extraction Overview MD to Extraction Finance MD
    builder.add_edge(summary_hsmt_node_v2.name, extraction_finance_md_node_v2.name)
    # 8->11
    # from Extraction Overview MD to Extraction Experience MD
    builder.add_edge(summary_hsmt_node_v2.name, extraction_experience_md_node_v2.name)
    #
    # from Extraction Overview MD to Extraction Technology MD
    builder.add_edge(summary_hsmt_node_v2.name, extraction_technology_md_node_v2.name)
    #
    # from Extraction Overview MD to Extraction Notice Bid MD
    builder.add_edge(summary_hsmt_node_v2.name, extraction_notice_bid_md_node_v2.name)
    # 9->12
    # from Extraction HR MD to Post-Extraction MD
    builder.add_edge(extraction_hr_md_node_v2.name, post_extraction_md_node_v2.name)
    # 10->12
    # from Extraction Finance MD to Post-Extraction MD
    builder.add_edge(extraction_finance_md_node_v2.name, post_extraction_md_node_v2.name)
    # 11->12
    # from Extraction Experience MD to Post-Extraction MD
    builder.add_edge(extraction_experience_md_node_v2.name, post_extraction_md_node_v2.name)
    #
    # from Extraction Overview MD to Extraction Technology MD
    builder.add_edge(extraction_technology_md_node_v2.name, post_extraction_md_node_v2.name)
    #
    # from Extraction Notice Bid MD to Extraction Technology MD
    builder.add_edge(extraction_notice_bid_md_node_v2.name, post_extraction_md_node_v2.name)
    # 12-> 13
    # from Post-Extraction to Generate Excel And Docx
    builder.add_edge(post_extraction_md_node_v2.name, END)
    # # 13-> END
    # # from Generate Excel And Docx to END
    # builder.add_edge(generate_excel_and_docx_node_v1.name, END)
    # Compile graph
    #
    

    graph = builder.compile(debug=False)
    finish_time = time.perf_counter()
    print(f"Total time build graph proposal_md_team_graph_v2_0_0 = {finish_time - start_time} s")
    return graph

print("[PROPOSAL_MD_TEAM_GRAPH_V2_0_0]    BUILDING... ")
proposal_md_team_graph_v2_0_0_instance = proposal_md_team_graph_v2_0_0()