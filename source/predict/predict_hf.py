'''Make predictions on the dataset using the model.'''
import os
cwd = os.getcwd()
if cwd.endswith("source/predict"):
	os.chdir("../..")  # change the working directory to the root directory
import sys
sys.path.append("source")
from configuration.configuration import Config
from model.hf_model import HFModel
from dataset.utils import load_data
import jsonlines
import time
from tqdm import tqdm
import argparse

if __name__ == "__main__":

	Parser = argparse.ArgumentParser()
	Parser.add_argument("--dataset_name", help="The name of the dataset.", choices=["GSM8K", "ASDiv", "MultiArith", "SVAMP", "AQUA", "date", "StrategyQA", "sports", "saycan", "CLUTRR"])
	Parser.add_argument("--split", help="The split of the dataset.", choices=["train", "dev", "test", "mydev", "mytest"])
	Parser.add_argument("--model_name", help="The name of the model (should have a corresponding config file under `configuration/config_files/dataset_name` called `{model_name}.json`.)")
	Parser.add_argument("--completion_only", help="Only query the LM to generate the completion (reasoning chain), but not execute the solver to derive the answer.", action="store_true")
	Parser.add_argument("--debug", help="If true, only run on the first 10 examples.", action="store_true")
	Parser.add_argument("--api_key_ids", help="The API keys to use.", default="['CCB']")

	args = Parser.parse_args()
	model_name = args.model_name
	dataset_name = args.dataset_name
	split = args.split
	debug = args.debug
	completion_only = args.completion_only

	config_frn = f"source/configuration/config_files/{dataset_name}/{model_name}.json"
	config = Config.from_json_file(config_frn)
	config.dataset_name = dataset_name
	config.split = split

	# load the dataset
	dataset_frn = f"data/{dataset_name}/{split}.jsonl"
	dataset = load_data(dataset_frn)

	# load the model
	model = HFModel(config)

	# predict
	output_dir = f"output_dir/{dataset_name}/{split}/{model_name}"
	if not os.path.exists(output_dir):
		os.makedirs(output_dir)

	output_fwn = f"{output_dir}/predictions{'_completion_only' if completion_only else ''}{'_debug' if debug else ''}.jsonl"

	# load existing predictions if any
	line_id = 0
	if os.path.isfile(output_fwn):
		with open(output_fwn, "r") as fr:
			reader = jsonlines.Reader(fr)
			for line_id, line in enumerate(reader):
				example_id = line["id"]
	if line_id > 0:
		start_id = line_id+1
	else:
		start_id = 0

	print(f"Making predictions on dataset {dataset_name} using model {model_name},\nstarting from the {start_id}th example...")

	with open(output_fwn, 'a') as fw:
		writer = jsonlines.Writer(fw, flush=True)
		t0 = time.time()
		for i, example in tqdm(enumerate(dataset), file=sys.stdout):
			if debug and i >= 10:
				break
			if i < start_id:
				continue
			question = example["question"]
			question_id = int(example["id"])
			try:
				output = model.predict(example, completion_only=completion_only)
				answer = output["answer"]
				completion = output["completion"]
				completions = output["completions"]
			except Exception as e:
				answer, completion, completions = "[error]", str(e), ""
				print(f"Error at example {i}: {str(e)}", file=sys.stderr)

			row = {"id": question_id,
			       "answer": answer,
			       "completion": completion,
			       "completions": completions
			       }
			writer.write(row)

		if i % 50 == 0:
			print(f"Finished {i} examples in {time.time() - t0} seconds.", flush=True)







