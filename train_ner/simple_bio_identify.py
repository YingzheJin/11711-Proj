import pandas as pd
from ast import literal_eval as load
import logging
from simpletransformers.ner import (
    NERArgs,
    NERModel,
)

labelset = ["B", "I", "O"]
type_ls = ['']

logging.basicConfig(level=logging.INFO)
transformers_logger = logging.getLogger("transformers")
transformers_logger.setLevel(logging.WARNING)

pos = pd.read_csv('../interim/pos_sent.csv')
pos = pos.dropna(axis=0, subset=['BIO'])
pos = pos.drop('bi_labels', axis=1)

def convert(df):
    data = []
    for i in range(len(df)):
        words = df.iloc[i, 1].split(' ')
        tags = load(df.iloc[i, 6])
        for j in range(len(words)):
            data.append([i, words[j], tags[j]])
    frame = pd.DataFrame(data, columns=['sentence_id', 'words', 'labels'])
    return frame

pos = pos.sample(frac=1, random_state=1)
bound = int(0.9*len(pos))
p_train = pos[:bound]
p_eval = pos[bound:]
train_df = convert(p_train)
eval_df = convert(p_eval)

def get_entity_spans(ls):
    # given a sequence of BIO taggs, get the list of tuples representing spans of entities
    spans = []
    for type in type_ls:
        for i in range(len(ls)):
            st, ed = 0, 0
            if ls[i] == 'B' + type:
                st, ed = i, i + 1
                for j in range(i+1, len(ls)):
                    if ls[j] == 'I' + type:
                        ed += 1
                    else:
                        break
                spans.append((st, ed))
    spans = sorted(spans, key=lambda x: x[0])
    return spans

def phrase_F1(ref, pred):
    TP = FP = FN = 0
    for k in range(len(pred)):
        # get the lists of predicted and reference tuples from the tag sequence
        pred_ls = get_entity_spans(pred[k])
        ref_ls = get_entity_spans(ref[k])
        # get the list of true positives tuples, and so on
        TPs = [i for i in pred_ls if i in ref_ls]
        FPs = [i for i in pred_ls if i not in ref_ls]
        FNs = [i for i in ref_ls if i not in pred_ls]
        TP += len(TPs)
        FP += len(FPs)
        FN += len(FNs)
    precision = TP / (TP + FP)
    recall = TP / (TP + FN)
    F1 = 2 * precision * recall / (precision + recall)
    print(f'precision: {precision}, recall: {recall}, F1: {F1}')
    return F1

model_args = NERArgs()
model_args.use_early_stopping = True
model_args.early_stopping_metric = "F1_score"
model_args.early_stopping_metric_minimize = False
model_args.early_stopping_patience = 2
model_args.early_stopping_consider_epochs = True
model_args.evaluate_during_training = True
model_args.evaluate_during_training_verbose = True

model_args.reprocess_input_data = True
model_args.overwrite_output_dir = True
model_args.output_dir='identify/'
model_args.best_model_dir='identify/best_model'
model_args.save_model_every_epoch = True
model_args.save_steps = -1
model_args.use_multiprocessing = False
model_args.manual_seed = 1
model_args.fp16 = False
model_args.num_train_epochs = 8
model_args.train_batch_size = 8
model_args.gradient_accumulation_steps = 4
model_args.learning_rate = 1e-5
model_args.scheduler = "polynomial_decay_schedule_with_warmup"
model_args.polynomial_decay_schedule_power = 0.5
model_args.do_lower_case = False

model = NERModel(
    'bert',
    'allenai/scibert_scivocab_cased',
    labels=labelset,
    args=model_args,
)

model.train_model(train_df, eval_df=eval_df,
                  F1_score=phrase_F1)
