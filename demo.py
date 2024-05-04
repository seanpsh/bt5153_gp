from transformers import (pipeline, 
    BertTokenizer, 
    BertForSequenceClassification, 
    AutoTokenizer, 
    AutoModelForTokenClassification,
    RobertaForTokenClassification,
    PreTrainedTokenizerFast,
    RobertaTokenizer
)
import hashlib
from datetime import datetime
import csv

def get_n_validate_user_opt():
    user_input_opt = input("Enter Option [detect (d) / detect & mask (dm)/ exit (e)]: ")
    input_clean = user_input_opt.upper().strip()
    if input_clean == 'D':
        return True, False
    # elif input_clean == 'MASK':
    #     return False, True
    elif input_clean == 'DM':
        return True, True
    elif input_clean == 'E':
        print('Exiting PII Detection Program')
        exit()
    else:
        print('[ERROR] Please re-enter option')
        return get_n_validate_user_opt()

def get_n_validate_user_input():
    user_input = input("Enter your text: ")
    if len(user_input) <= 1500:
        return user_input
    else:
        print('[ERROR] - Text exceeded max length of 512, please reduce.')
        return get_n_validate_user_input()

def get_n_validate_mask_option():
    user_input_mask = input("Enter masking method [NA (na), Redact (re) , Encrypt (en), Obfuscation (ob)] ")
    masking_option = ['NA', 'RE', 'EN', 'OB']
    input_clean = user_input_mask.upper().strip()
    if input_clean == 'EN':
        curr_dt = datetime.now().strftime("%Y%m%d%H%M%S")
        en_file = f'data/encryption/{curr_dt}.csv'
        with open(en_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            header = ['hash', 'tag', 'value']
            writer.writerow(header)
        return input_clean, en_file
    elif input_clean in masking_option:
        return input_clean, ''
    else:
        print('[ERROR] - please enter only the options provided.')
        return get_n_validate_mask_option()

def replace_with_tag(input, start, end, tag, mask, en_file):
    if mask == 'NA':
        pass
    elif mask == 'RE':
        tag = 'REDACTED'
    elif mask == 'EN':
        org_txt = input[start:end].upper()
        input_bytes = org_txt.encode('utf-8')

        sha256_hash = hashlib.sha256()
        sha256_hash.update(input_bytes)
        txt_hash = sha256_hash.hexdigest()

        with open(en_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            row = [txt_hash, tag, org_txt]
            writer.writerow(row)
        
        tag = txt_hash

    return input[:start] + f"[{tag}]" + input[end:], tag



def detect_pii(user_input, mask='NA', en_file=''):
     # Path to the saved model directory
    model_path = "roberta_best"

    # Load the tokenizer and model from the saved directory
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = RobertaForTokenClassification.from_pretrained(model_path)

    # Create a pipeline for sequence classification
    classifier = pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer
    )

    # Perform prediction
    predictions = classifier(user_input)
    # print(predictions) #print the detected tags
    if len(predictions) == 0:
        detect_flg = 'No PII Detected'
        return detect_flg, user_input, ''

    detect_flg = 'PII Detected'
    user_input_detect = user_input
    # tag = ''
    # tag_range = []
    # tag_cnt = 0

    formatted_results = []
    for result in predictions:
        # print(result)
        end = result["start"] + len(result["word"].replace("Ġ", " "))
        # print(end)
        if formatted_results and formatted_results[-1]["entity"][0] == "B" and result["entity"][0] == "I":
            formatted_results[-1]["end"] = end
            formatted_results[-1]["word"] += result["word"].replace("Ġ", " ")
        else:
            formatted_results.append({
                'start': result["start"],
                'end': end,
                'entity': result["entity"],
                'index': result["index"],
                'score': result["score"],
                'word': result["word"]
            })

    if mask != 'OB':
        offset = 0
        for tk in formatted_results:
            # print(tk)
            tag_lb = tk['entity']
            if tag_lb[0] == 'B':
                tag = tag_lb.split('-')[1]
                # print(tag)
                tag_start = tk['start']+ offset
                tag_end = tk['end']+ offset
                tag_range = [tag_start, tag_end]

            # elif tag_lb[0] == 'I' and tag != '':
            #     tag_range[1] = int(tk['end'])
                user_input_detect, tag = replace_with_tag(user_input_detect,
                                                    tag_range[0] ,
                                                    tag_range[1] ,
                                                    tag,
                                                    mask,
                                                    en_file)
                offset += len(tag) + 2 - tk["end"] + tk["start"]

            # tag_range = []
            # tag = tag_lb.split('-')[1]
            # tag_start = int(tk['start'])
            # tag_end = int(tk['end'])
            # tag_range = [tag_start, tag_end]
            else:
                print('[ERROR] - Tag Error')
                exit()

    if mask == 'OB':
        for result in formatted_results:
            entity_tag = result["entity"].split("-")[-1]
            start = result["start"]
            end = result["end"]
            if entity_tag in ['NAME_STUDENT', 'PHONE_NUM', 'USERNAME', 'ID_NUM', 'STREET_ADDRESS']:
                word = result['word'][1:]
                masked_word = word[0] + 'x' * (len(word) - 1)
                user_input_detect = user_input_detect[:start] + masked_word + user_input_detect[end:]
            elif entity_tag == 'EMAIL':
                email_address = result["word"][1:]
                username, domain = email_address.split("@")
                masked_username = username[0] + "x" * (len(username) - 1)
                masked_email = masked_username + "@" + domain
                user_input_detect = user_input_detect[:start] + masked_email + user_input_detect[end:]
            elif entity_tag == 'URL_PERSONAL':
                url = result["word"]
                print(url)
                https_part = "https://"
                masked_part = "x" * (len(url) - len(https_part))
                masked_url = https_part + masked_part
                user_input_detect = user_input_detect[:start] + masked_url + user_input_detect[end:]
            user_input_detect = user_input_detect


        # tag_cnt += 1
        # handle the last tag
        # user_input_detect = replace_with_tag(user_input_detect,
        #                             tag_range[0] + 66*tag_cnt,
        #                             tag_range[1] + 66*tag_cnt,
        #                             tag,
        #                             mask,
        #                             en_file)
    return detect_flg, user_input_detect, formatted_results


def main():
    while True:
        detection, masking = get_n_validate_user_opt()
        if detection and masking:
            user_input = get_n_validate_user_input()
            mask, en_file = get_n_validate_mask_option()
            detect_flg, text_out, formatted_results = detect_pii(user_input, mask, en_file)
            print('Detect_status:', detect_flg)
            print('\nDetected Text:')
            for result in formatted_results:
                print(
                    f"""Entity: {result["entity"]}, Start:{result["start"]}, End:{result["end"]}, word:{user_input[result["start"]:result["end"]]}""")

            print('\nMasked Text: ', text_out)
        elif detection:
            user_input = get_n_validate_user_input()
            detect_flg, text_out, formatted_results = detect_pii(user_input)
            print('Detect_status:', detect_flg)
            for result in formatted_results:
                print(
                    f"""Entity: {result["entity"]}, Start:{result["start"]}, End:{result["end"]}, word:{user_input[result["start"]:result["end"]]}""")
        else:
            pass


if __name__ == "__main__":
    main()

