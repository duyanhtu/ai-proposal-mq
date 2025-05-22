# Standard imports
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Third party imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import MarkdownTextSplitter

# Your imports
from app.model_ai import llm
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")

class ExtractionTechnologyNodeV2m0p0:
    """
        ExtractionTechnologyNodeV2m0p0
    """

    def __init__(self, name: str):
        self.name = name

    def __call__(self, state: StateProposalV1):
        logger.info(f"Running node: {self.name}")
        try:
            start_time = time.perf_counter()

            input_contents = [
                *state.get("document_content_markdown_hskt", []),
                *state.get("document_content_markdown_tcdgkt", [])
            ]
            if not input_contents:
                return {"result_extraction_technology": {}}

            all_results = []
            with ThreadPoolExecutor(max_workers=2) as outer_executor:
                results = list(outer_executor.map(self.process_one_document, input_contents))
                for r in results:
                    all_results.extend(r)

            merged = self._merge_technical_results(all_results)
            final_result = self._format_merged_output(merged)

            elapsed = time.perf_counter() - start_time
            logger.info(f"{self.name} completed in {elapsed:.2f}s")

            return {"result_extraction_technology": final_result}
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}",
                include_trace=True
            )
            return {
                "result_extraction_technology": {},
                "error_messages": [error_msg],
            }

    def process_one_document(self, content: str):
        """Xử lý từng chương: chia chunk rồi xử lý song song từng chunk."""
        markdown_splitter = MarkdownTextSplitter(
            chunk_size=10000,
            chunk_overlap=200,
            keep_separator=False
        )
        chunks = markdown_splitter.split_text(content)

        def process_chunk(chunk: str, chunk_idx: int):
            logger.debug(f"[Chunk {chunk_idx+1}/{len(chunks)}] Input: {chunk[:300]!r}")
            try:
                prompt_template = self._get_prompt_template()
                prompt = ChatPromptTemplate.from_template(prompt_template).invoke({"content": chunk})
                response = (
                    llm.chat_model_gpt_4o_mini_16k()
                    .with_structured_output(None, method="json_mode")
                    .invoke(prompt)
                )
                logger.debug(f"[Chunk {chunk_idx+1}] Output: {response}")
                if isinstance(response, list):
                    return response
                elif isinstance(response, dict) and response:
                    return [response]
                return []
            except Exception as e:
                logger.error(f"Error in chunk {chunk_idx+1}: {e}")
                return []

        chunk_results = []
        with ThreadPoolExecutor(max_workers=4) as inner_executor:
            futures = [inner_executor.submit(process_chunk, chunk, i) for i, chunk in enumerate(chunks)]
            for future in futures:
                chunk_results.extend(future.result())
        return chunk_results

    def _format_merged_output(self, merged_results):
        merged = {
            "hr": [],
            "requirement_level_0": {
                "muc": "1.",
                "requirement_name": "Yêu cầu về kỹ thuật",
                "sub_requirements": []
            }
        }

        hr_seen = set()

        for item in merged_results:
            if not isinstance(item, dict):
                continue

            # Gộp thông tin nhân sự
            hr_list = item.get("hr", [])
            for hr_item in hr_list:
                hr_key = (
                    hr_item.get("position", ""),
                    hr_item.get("quantity", "0"),
                    tuple(
                        (req.get("name", ""), req.get("description", ""))
                        for req in hr_item.get("requirements", [])
                    )
                )
                if hr_key not in hr_seen:
                    hr_seen.add(hr_key)
                    merged["hr"].append(hr_item)

            # Gộp các yêu cầu kỹ thuật
            sub_reqs = item.get("requirement_level_0", {}).get("sub_requirements", [])
            merged["requirement_level_0"]["sub_requirements"].extend(sub_reqs)

        return merged

    def _get_prompt_template(self):
        """Return the prompt template for extraction"""
        return """
            Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
            Hãy lấy tất cả các yêu cầu liên quan đến nhân sự và các yêu cầu còn lại bao gồm: yêu cầu kỹ thuật và các yêu cầu khác không liên quan đến nhân sự trong file được cung cấp.
            **CHÚ Ý:** PHẢI lấy đầy đủ nội dung yêu cầu và mô tả chi tiết yêu cầu trong tài liệu theo dữ liệu gốc.
                    Nếu trong file không có yêu cầu liên quan đến nhân sự thì để trống phần nhân sự.
                    Không lấy các thông tin về giới thiệu chung về gói thầu.
                    KHông lấy thông tin phạm vi gói thầu
                    KHÔNG tách nội dung mô tả để làm yêu cầu
                   
            2. Đối với dữ liệu yêu cầu trong bảng yêu cầu được viết trong 1 đoạn (ngăn cách bằng |   |) với
                - Nội dung cần trích xuất bắt đầu từ dấu `|` và kết thúc ngay trước dấu `|` tiếp theo (hoặc hết nội dung nếu không có dấu `|` tiếp theo).
                - Giữ nguyên toàn bộ nội dung gốc trong khoảng giữa hai dấu `|`, bao gồm cả định dạng văn bản, ký tự xuống dòng, hoặc ký tự đặc biệt nếu có, xóa dấu `|`.
                - Trong nội dung có các chú ý trong dấu () thì hãy lấy hết nội dung trong ngoặc đó như Điều khoản (3), Nghị định (8), Tiết (e), v.v.
                - Nếu dạng table thì mỗi row cho vào 1 description_detail riêng biệt.
                - KHông lấy tiêu đề cột trong bảng để làm yêu cầu.(ví dụ Thông số kỹ thuật/Yêu cầu dịch vụ  là tên cột của bảng yêu cầu cần bóc tách thì không đưa thành yêu cầu)
            3.Đối với dữ liệu không nằm trong bảng lấy yêu cầu theo heading( hoặc -)
            5. Bỏ qua các chỉ mục ví dụ 3.1, 3.2,.... và lấy đúng tên yêu cầu cần lấy.
           
            6. Ví dụ chỉ để tham khảo KHÔNG phải là nội dung cần bóc tách.
            7. Đầu ra hãy trả về dạng JSON.
 
            **Ví dụ**
            Ví dụ 1: có input như sau:
            **3.3 Yêu cầu nội dung công việc bảo trì**
            3.3.1 Yêu cầu chung

                -Kiểm tra, bảo trì định kỳ: Trong thời gian bảo trì, định kỳ tối thiểu 03 tháng/01 lần (hoặc ngay khi có yêu cầu của Agribank) thực hiện kiểm tra, bảo dưỡng định kỳ cho các thiết bị thuộc phạm vi bảo trì, rà soát cấu hình, đánh giá hiệu năng sử dụng, đưa ra các khuyến nghị để tối ưu thiết bị (nếu có).

                - Hỗ trợ kỹ thuật và xử lý, khắc phục sự cố: Trong thời gian bảo trì, đơn vị cung cấp dịch vụ bảo trì phải cung cấp dịch vụ hỗ trợ kỹ thuật và khắc phục sự cố thiết bị. Khi có yêu cầu hỗ trợ kỹ thuật của Agribank hoặc khi thiết bị có sự cố, đơn vị cung cấp dịch vụ bảo trì có trách nhiệm hỗ trợ kỹ thuật và xử lý, khắc phục sự cố; trường hợp cần thiết đơn vị cung cấp dịch vụ bảo trì phải cử cán bộ trực tiếp tới địa điểm lắp đặt thiết bị hoặc yêu cầu hỗ trợ trợ kỹ thuật của hãng sản xuất để xử lý và khắc phục sự cố trong thời gian sớm nhất.
                - Cập nhật phần mềm hệ điều hành và phần mềm an ninh phòng chống tấn công xâm nhập (IPS) của thiết bị: Trong thời gian bảo trì, các thiết bị phải được thường xuyên, liên tục cập nhập phần mềm hệ điều hành thiết bị, bản vá lỗi, phần mềm an ninh phòng chống tấn công xâm nhập và các mẫu tấn công xâm nhập mới theo tiêu chuẩn của hãng sản xuất. Căn cứ các khuyến nghị/khuyến cáo của hãng sản

                3

                xuất, yêu cầu của Agribank, đơn vị cung cấp phải chủ động tiến hành phân tích, lên kế hoạch để nâng cấp, cập nhật kịp thời nhằm giúp các thiết bị tường lửa hoạt động an toàn, ổn định, ngăn ngừa các lỗi và sự cố ảnh hưởng đến hoạt động hệ thống mạng.
            Output mong muốn như sau:
            [
                {{	"hr": [             
                    ]
                }},
                
                    {{ "requirement_level_0": {{
                        "muc": "3",
                        "requirement_name": "Yêu cầu về kỹ thuật",
                        "sub_requirements": [
                            {{
                                "requirement_level_1": {{
                                    "muc": "3.3",
                                    "requirement_name": "Yêu cầu nội dung công việc bảo trì",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "3.3.1",
                                                "requirement_name": "Yêu cầu chung",
                                                "description": [
                                                    {{
                                                        "description_detail": "Kiểm tra, bảo trì định kỳ: Trong thời gian bảo trì, định kỳ tối thiểu 03 tháng/01 lần (hoặc ngay khi có yêu cầu của Agribank) thực hiện kiểm tra, bảo dưỡng định kỳ cho các thiết bị thuộc phạm vi bảo trì, rà soát cấu hình, đánh giá hiệu năng sử dụng, đưa ra các khuyến nghị để tối ưu thiết bị (nếu có)."
                                                    }},
                                                    {{
                                                        "description_detail": "Hỗ trợ kỹ thuật và xử lý, khắc phục sự cố: Trong thời gian bảo trì, đơn vị cung cấp dịch vụ bảo trì phải cung cấp dịch vụ hỗ trợ kỹ thuật và khắc phục sự cố thiết bị. Khi có yêu cầu hỗ trợ kỹ thuật của Agribank hoặc khi thiết bị có sự cố, đơn vị cung cấp dịch vụ bảo trì có trách nhiệm hỗ trợ kỹ thuật và xử lý, khắc phục sự cố; trường hợp cần thiết đơn vị cung cấp dịch vụ bảo trì phải cử cán bộ trực tiếp tới địa điểm lắp đặt thiết bị hoặc yêu cầu hỗ trợ trợ kỹ thuật của hãng sản xuất để xử lý và khắc phục sự cố trong thời gian sớm nhất."
                                                    }},
                                                    {{
                                                        "description_detail": "Cập nhật phần mềm hệ điều hành và phần mềm an ninh phòng chống tấn công xâm nhập (IPS) của thiết bị: Trong thời gian bảo trì, các thiết bị phải được thường xuyên, liên tục cập nhập phần mềm hệ điều hành thiết bị, bản vá lỗi, phần mềm an ninh phòng chống tấn công xâm nhập và các mẫu tấn công xâm nhập mới theo tiêu chuẩn của hãng sản xuất. Căn cứ các khuyến nghị/khuyến cáo của hãng sản xuất, yêu cầu của Agribank, đơn vị cung cấp phải chủ động tiến hành phân tích, lên kế hoạch để nâng cấp, cập nhật kịp thời nhằm giúp các thiết bị tường lửa hoạt động an toàn, ổn định, ngăn ngừa các lỗi và sự cố ảnh hưởng đến hoạt động hệ thống mạng."
                                                    }}
                                                ]
                                            }}
                                        }},
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "3.3.2",
                                                "requirement_name": "Yêu cầu về công việc kiểm tra, bảo trì định kỳ",
                                                "sub_requirements": [
                                                    {{
                                                        "requirement_level_3": {{
                                                            "muc": "a",
                                                            "requirement_name": "Kiểm tra, vệ sinh thiết bị",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "Kiểm tra môi trường hoạt động của thiết bị, nguồn điện, nhiệt độ."
                                                                }},
                                                                {{
                                                                    "description_detail": "Kiểm tra dây cáp, đầu kết nối mạng. Sắp xếp gọn gàng và cố định các dây cáp kết nối mạng trên thiết bị."
                                                                }},
                                                                {{
                                                                    "description_detail": "Thực hiện bảo dưỡng, vệ sinh thiết bị, nguồn, cổng kết nối, module SFP."
                                                                }}
                                                            ]
                                                        }}
                                                    }},
                                                    {{
                                                        "requirement_level_3": {{
                                                            "muc": "b",
                                                            "requirement_name": "Kiểm tra hoạt động, cấu hình và chính sách an ninh của thiết bị",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "Kiểm tra hiệu năng hoạt động của thiết bị: khả năng đáp ứng tài nguyên của bộ vi xử lý (CPU) và bộ nhớ (RAM)."
                                                                }}
                                                            ]
                                                        }}
                                                    }},
                                                    {{
                                                        "requirement_level_3": {{
                                                            "muc": "c",
                                                            "requirement_name": "Tối ưu cấu hình và chính sách an ninh mạng trên thiết bị",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "Rà soát các cấu hình và chính sách an ninh mạng được thiết lập trên thiết bị."
                                                                }}
                                                            ]
                                                        }}
                                                    }}
                                                ]
                                            }}
                                        }}
                                    ]
                                }}
                            }}
                        ]
                    }}

            ]
            ví dụ 2: 
            OUTPUT NHƯ SAU:
            {{	"hr": [             
                    ]
            }},
            {{
                "requirement_level_0": {{
                    "muc": "1.",
                    "requirement_name": "Yêu cầu về kỹ thuật",
                    "sub_requirements": [
                        {{
                            "requirement_level_1": {{
                                "muc": "1.2.",
                                "requirement_name": "Yêu cầu về kỹ thuật",
                                "sub_requirements": [
                                    {{
                                        "requirement_level_2": {{
                                            "muc": "1",
                                            "requirement_name": "Bản quyền phần mềm Microsoft Office LTSC Standard 2021",
                                            "description": [
                                                {{
                                                    "description_detail": "Đảm bảo tương thích với hệ điều hành Windows 10, Windows 11"
                                                }},
                                                {{
                                                    "description_detail": "Bao gồm các ứng dụng cơ bản như Word, Excel, PowerPoint và Outlook."
                                                }}
                                            ]
                                        }}
                                    }}
                                ]
                            }},
                            "requirement_level_1": {{
                                "muc": "1.3.",
                                "requirement_name": "Các yêu cầu khác",
                                "sub_requirements": [
                                    {{
                                        "requirement_level_2": {{
                                            "muc": "1.3.1",
                                            "requirement_name": "Yêu cầu về Bản quyền",
                                            "description": [
                                                {{
                                                    "description_detail": "- Hàng hóa cung cấp mới 100% chưa qua sử dụng"
                                                }},
                                                {{
                                                    "description_detail": "- Có Giấy phép hoặc giấy ủy quyền bán hàng của nhà sản xuất, đại lý phân phối hoặc giấy chứng nhận quan hệ đối tác hoặc tài liệu khác có giá trị tương đương."
                                                }}
                                            ]
                                        }}
                                    }},
                                    {{
                                        "requirement_level_2": {{
                                            "muc": "1.3.2",
                                            "requirement_name": "Yêu cầu về bảo hành, hỗ trợ kỹ thuật",
                                            "description": [
                                                {{
                                                    "description_detail": "Nhà thầu phải có văn phòng hoặc cơ sở tại Hà Nội "
                                                }},
                                            ]
                                        }}
                                    }}
                                ]
                            }}
                        }}
                    ]
                }}
            }}

            ví dụ 3:
                
                {{	"hr": [
                        {{
                            "position": "Trưởng nhóm triển khai",
                            "quantity": "1",
                            "requirements": [
                                {{
                                    "name": "",
                                    "description": "- Tối thiểu 03 năm hoặc tối thiểu 01 hợp đồng."
                                }},
                                {{
                                    "name": "",
                                    "description": "- Tốt nghiệp Đại học chuyên ngành Công nghệ thông tin, An toàn thông tin hoặc Điện tử viễn thông, Điện tử truyền thông."
                                }},
                                {{
                                    "name": "",
                                    "description": "- Có chứng nhận hoặc chứng chỉ chứng minh đã được đào tạo về sản phẩm chào thầu"
                                }}					
                            ]                
                        }}
                    ]
                }},
                {{  "requirement_level_0": {{
                    "muc": "1.",
                    {{
                        "requirement_name": "Yêu cầu về kỹ thuật",
                        "sub_requirements": [
                            {{
                                "requirement_level_1": {{
                                    "muc": "1.2.",
                                    "requirement_name": "Yêu cầu về kỹ thuật",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "1",
                                                "requirement_name": "Bản quyền phần mềm Microsoft Office LTSC Standard 2021",
                                                "description": [
                                                    {{
                                                        "description_detail": "Đảm bảo tương thích với hệ điều hành Windows 10, Windows 11"
                                                    }},
                                                    {{
                                                        "description_detail": "Bao gồm các ứng dụng cơ bản như Word, Excel, PowerPoint và Outlook."
                                                    }}
                                                ]
                                            }}
                                        }}
                                    ]
                                }}
                            }}
                        ]
                    }}
                }}
            }}
            Return only the JSON in this format:
                    
            [
                {{"hr": [
                        {{
                            "position": "Vị trí công việc, nếu không có yêu cầu bắt buộc để giá trị rỗng",
                            "quantity": "Số lượng yêu cầu, nếu không có yêu cầu bắt buộc để giá trị 0",
                            "requirements": [
                                {{
                                    "name": "tên yêu cầu, nếu không có yêu cầu bắt buộc để giá trị rỗng",
                                    "description": "mô tả chi tiết của yêu cầu, nếu không có yêu cầu bắt buộc để giá trị rỗng"
                                }}
                            ]                
                        }}
                    ]
                }},	
                {{
                    "requirement_level_0": {{
                        "muc": "số chỉ mục",
                        "requirement_name": "Yêu cầu kỹ thuật",
                        "sub_requirements": [
                            {{
                                "requirement_level_1": {{
                                    "muc": "số chỉ mục",
                                    "requirement_name": "tên yêu cầu là các yêu cầu trong phạm vi mô tả ở trên có level nhỏ hơn level 0",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "số chỉ mục",
                                                "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 1",
                                                "sub_requirements": [
                                                    {{
                                                        "requirement_level_3": {{
                                                            "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 2",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "mô tả từng chi tiết của yêu cầu"
                                                                }}
                                                            ]
                                                        }}
                                                    }}
                                                ]
                                            }}
                                        }}
                                    ]
                                }}
                            }}
                        ]
                    }}
                }}
            ]                                       
                        
            Nội dung hồ sơ mời thầu:
                {content}
    """

    def _merge_technical_results(self, results):
        """Merge technical requirements from different chunks"""
        if not results:
            return []

        # Simple approach: if each chunk returns a list of requirements at level 0,
        # we can concatenate them
        merged = []

        for result in results:
            # Skip empty results
            if not result:
                continue

            # Handle different result structures
            if isinstance(result, list):
                merged.extend(result)
            elif isinstance(result, dict) and "requirement_level_0" in result:
                merged.append(result)

        return merged
