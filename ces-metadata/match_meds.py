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
NO_GOOD_MATCH_CSV = './intermediates/hum-no-match-1.csv'


def main():
    ssa_csv = clean_csv_list(csv_as_list(SSA_CSV))
    hum_csv = clean_csv_list(csv_as_list(HUM_CSV))

    # list[str, str, str, str]
    #   ssa_code, ssa_name, moa, clean_ssa_name
    ssa_lines = [(l[0], l[1], l[2], clean_ssa_drug_name(l[1])) for l in ssa_csv]

    # create a dict [ICD code -> HUM drug name]
    # this also serves to de-duplicate ICD codes
    # dict[str: str]
    #   icd_code: hum_name
    hum_codes_to_drug_names = {
        l[3]: clean_hum_drug_name(l[2])
        for l in hum_csv }

    # list[tuple(tuple(ssa_csv_line), tuple(str, int, str))]
    #   (ssa_code, ssa_name, moa, clean_ssa_name), (hum_name, score, icd_code)
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

    print('\nOkay, now to sort through the remaining HUM drugs.')
    # [icd_code, clean_hum_name]
    hum_remainder = [l for l in hum_codes_to_drug_names.items()
                     if l[1] not in good_matches_formatted[4]]
    print('COMPARING:')
    print(next(hum_codes_to_drug_names.items().__iter__())[1])
    print(good_matches_formatted[0][4])
    print()
    print('{} drugs remain of {} from the HUM list'.format(
        len(hum_remainder), len(hum_codes_to_drug_names)))
    print('Writing a csv of this remainder: ' + NO_GOOD_MATCH_CSV)
    write_to_csv(hum_remainder, NO_GOOD_MATCH_CSV)

    print("Let's see if there are any less-obvious matches")
    for (code, hum_name) in hum_remainder:
        print(hum_name, '\t', code)
        ssa_clean_names = { l[3] for l in ssa_lines }
        matches = process.extract(hum_name, ssa_clean_names, limit=3)
        for i, match in enumerate(matches):
            print('{}) {}'.format(i + 1, match))
        print('{}) None'.format(len(matches)))
        selection = input('Any of these look right? ')


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

