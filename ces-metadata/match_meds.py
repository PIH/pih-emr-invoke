#! env/bin/python3
"""
match_meds.py

Attempts to match the medications listed in
meds-ssa.csv and meds-ces.csv to PIH and CIEL concept codes
found in HUM_Drug_List.
"""
import csv
import re

from fuzzywuzzy import process

SSA_CSV = './input/meds-ssa.csv'
HUM_CSV = './input/HUM_Drug_List-13.csv'
GOOD_MATCHES_CSV = './output/meds-ssa-matches-1.csv'
CHOICE_MATCHES_CSV = './output/meds-ssa-matches-2.csv'
NO_GOOD_MATCH_CSV = './intermediates/hum-no-match-1.csv'


def main():
    ssa_csv = clean_csv_list(csv_as_list(SSA_CSV))
    hum_csv = clean_csv_list(csv_as_list(HUM_CSV))

    # [ssa_code, ssa_name, moa, clean_ssa_name]
    ssa_lines = [(l[0], l[1], l[2], clean_ssa_drug_name(l[1])) for l in ssa_csv]

    # create a dict [ICD code -> HUM drug name]
    # this also serves to de-duplicate ICD codes
    # {icd_code: clean_hum_name}
    hum_codes_to_drug_names = {
        l[3]: clean_hum_drug_name(l[2])
        for l in hum_csv }

    # let's keep another with the full hum_name, for reference
    hum_codes_to_full_drug_names = { l[3]: l[2] for l in hum_csv }

    # [(ssa_code, ssa_name, moa, clean_ssa_name), (hum_name, score, icd_code)]
    matches = [(l, process.extractOne(l[3], hum_codes_to_drug_names))
               for l in ssa_lines]
    good_matches = [m for m in matches if m[1][1] > 80]

    print('Found %d very good matches:' % len(good_matches))
    for m in good_matches:
        # ssa_name, hum_name, icd_code
        print('{}\t=\t{}\t{}'.format(m[0][1], m[1][0], m[1][2]))
    print('\nThese will be put in file ' + GOOD_MATCHES_CSV)

    # [ssa_code, ssa_name, moa, icd_code, clean_hum_name]
    good_matches_formatted = [[m[0][0], m[0][1], m[0][2], m[1][2], m[1][0]] for m in good_matches]
    write_to_csv(good_matches_formatted, GOOD_MATCHES_CSV)

    print('\nOkay, now to sort through the remaining drugs.')
    # [clean_ssa_name]
    matched_clean_ssa_names = [l[0][3] for l in good_matches]
    # [ssa_code, ssa_name, moa, clean_ssa_name]
    ssa_remainder = [l for l in ssa_lines if l[3] not in matched_clean_ssa_names]
    print('{} drugs remain of {} from the SSA list'.format(
        len(ssa_remainder), len(ssa_lines)))
    print('Writing a csv of this remainder: ' + NO_GOOD_MATCH_CSV)
    write_to_csv(ssa_remainder, NO_GOOD_MATCH_CSV)

    print("Let's see if there are any less-obvious matches")
    # [ssa_code, ssa_name, moa, icd_code, clean_hum_name]
    choice_matches = []
    for ssa_linenum, ssa_line in enumerate(ssa_remainder):
        print(ssa_line[1])
        matches = process.extract(ssa_line[3], hum_codes_to_drug_names, limit=3)
        for i, match in enumerate(matches):
            full_hum_name = hum_codes_to_full_drug_names[match[2]]
            print('{}) {}\t({}),\te.g. {}'.format(i + 1, match[0], match[2], full_hum_name))
        print('4) None of these')
        choice_num = None
        while choice_num is None:
            choice_input = input('Any of these look right? ')
            try:
                choice_num = int(choice_input) - 1  # the user input numbers are 1-indexed
            except ValueError:
                print('{} is not a valid input. Try again.'.format(choice_input))
        if choice_num in range(len(matches)):
            choice = matches[choice_num]
            choice_matches.append([ssa_line[0], ssa_line[1], ssa_line[2], choice[2], choice[0]])
            write_to_csv(choice_matches, CHOICE_MATCHES_CSV)
        print()


def csv_as_list(filename):
    with open(filename, 'rt', encoding='utf8') as csvfile:
        reader = csv.reader(csvfile)
        return list(reader)


def clean_csv_list(input_list):
    """Drops blank lines & the header line"""
    return [l for l in input_list if l != []][1:]


def clean_hum_drug_name(drug_name):
    drug_name = drug_name.lower()
    result = re.split(r',|\d', drug_name)[0].strip()
    return result


def clean_ssa_drug_name(drug_name):
    drug_name = drug_name.lower()
    result = re.split(r',|de|-|\(|\d', drug_name)[0].strip()
    if result == '':
        result = drug_name.split()[0]
        print('WARNING: clean_ssa_drug_name reduced drug name to empty string. Using ' + result)
    return result


def write_to_csv(data, filename):
    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)


if __name__ == "__main__":
    main()

