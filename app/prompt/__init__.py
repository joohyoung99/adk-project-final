from app.prompt.instructions import (
    supervisor_instruction,

    rag_rewrite_instruction,
    rag_answer_instruction,
    rag_search_instruction,

    parallel_rewrite_instruction,
    parallel_web_search_instruction,
    parallel_rag_search_instruction,
    parallel_merge_instruction,
    parallel_answer_instruction,

    docu_rewrite_instruction,
    docu_generation_instruction,

)

__all__ = [
    "supervisor_instruction",

    "rag_rewrite_instruction",
    "rag_search_instruction",
    "rag_answer_instruction",
    
   
    "parallel_rewrite_instruction",
    "parallel_web_search_instruction",
    "parallel_rag_search_instruction",
    "parallel_merge_instruction",
    "parallel_answer_instruction",
    
    "docu_rewrite_instruction",
    "docu_generation_instruction",

]
