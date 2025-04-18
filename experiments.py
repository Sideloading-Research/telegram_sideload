from config import EXPENDABLE_MINDFILE_PART, REPO_URL, DATASET_LOCAL_DIR_PATH

from utils.mindfile import build_source_tags, refresh_local_mindfile_data, get_system_message_and_context, split_context_by_importance
from utils.text_shrinkage import shrink_text

files_dict = refresh_local_mindfile_data(REPO_URL, DATASET_LOCAL_DIR_PATH)
system_message, context = get_system_message_and_context(files_dict, save_context_to_file7=True)

before_expendable, expendable, after_expendable = split_context_by_importance(context)

"""
print("#"*100)
print(f"Before expendable: {len(before_expendable)}")
print(before_expendable[:100])
print("(skip)")
print(before_expendable[-100:])
print("#"*100)
print(f"Expendable: {len(expendable)}")
print(expendable[:100])
print("(skip)")
print(expendable[-100:])
print("#"*100)
print(f"After expendable: {len(after_expendable)}")
print(after_expendable[:100])
print("(skip)")
print(after_expendable[-100:])
"""

res = shrink_text(expendable, 120000)

# write to file
with open("expendable_shrinked.txt", "w") as f:
    f.write(res)
