#! env/bin/python3
"""
match_meds.py

Attempts to match the medications listed in
meds-ssa.csv and meds-ces.csv to PIH and CIEL concept codes
found in HUM_Drug_List.
"""
import csv
import json
import os
import re

from fuzzywuzzy import fuzz, process
from tqdm import tqdm

SSA_CSV = "./input/meds-ssa.csv"
HUM_CSV = "./input/HUM_Drug_List-13.csv"
CIEL_JSON = "./input/meds-ciel.json"

MATCHES_HUM_AUTO_CSV = "./output/meds-matches-hum-auto.csv"
UNMATCHED_HUM_AUTO_CSV = "./intermediates/no-match-hum-auto.csv"
MATCHES_CIEL_AUTO_CSV = "./output/meds-matches-ciel-auto.csv"
UNMATCHED_CIEL_AUTO_CSV = "./intermediates/no-match-ciel-auto.csv"

CHOICE_MATCHES_INTERMEDIATE_CSV = "./intermediates/choice-matches.csv"
MATCHES_CHOICE_CSV = "./output/meds-matches-choice.csv"
UNMATCHED_CHOICE_INTERMEDIATE_CSV = "./intermediates/no-match-choice.csv"
UNMATCHED_CSV = "./ouput/meds-unmatched.csv"

HUM_MATCH_SCORE_LIMIT = 80
CIEL_MATCH_SCORE_LIMIT = 70


def main():
    ssa_csv = clean_csv_list(csv_as_list(SSA_CSV))
    hum_csv = clean_csv_list(csv_as_list(HUM_CSV))
    # [ssa_code, ssa_name, moa, clean_ssa_name]
    ssa_lines = [(l[0], l[1], l[2], clean_ssa_drug_name(l[1])) for l in ssa_csv]
    ciel_data = from_json_file(CIEL_JSON)

    skipped_hum_auto = False
    if os.path.isfile(MATCHES_HUM_AUTO_CSV) and os.path.isfile(UNMATCHED_HUM_AUTO_CSV):
        print("\nAutomatic matches from HUM found in " + MATCHES_HUM_AUTO_CSV + "and")
        print("Unmatched after HUM auto found in " + UNMATCHED_HUM_AUTO_CSV)
        skipped_hum_auto = True
    else:
        print("\nExtracting good matches from HUM...")
        matches, unmatched_ssa_lines = extract_good_matches_hum(ssa_lines, hum_csv)
        save_matches_and_unmatched(
            matches, unmatched_ssa_lines, MATCHES_HUM_AUTO_CSV, UNMATCHED_HUM_AUTO_CSV
        )

    skipped_ciel_auto = False
    if os.path.isfile(MATCHES_CIEL_AUTO_CSV):
        print("\nAutomatic matches from CIEL found in " + MATCHES_CIEL_AUTO_CSV + "and")
        print("Unmatched after CIEL auto found in " + UNMATCHED_CIEL_AUTO_CSV)
        skipped_ciel_auto = True
    else:
        print("\nExtracting good matches from CIEL...")
        if skipped_hum_auto:
            unmatched_ssa_lines = csv_as_list(UNMATCHED_HUM_AUTO_CSV)
        matches, unmatched_ssa_lines = extract_good_matches_ciel(
            unmatched_ssa_lines, ciel_data
        )
        save_matches_and_unmatched(
            matches, unmatched_ssa_lines, MATCHES_CIEL_AUTO_CSV, UNMATCHED_CIEL_AUTO_CSV
        )

    print("\nOkay, now to sort through the remaining drugs.")
    print("Always prefer one of the first two matches, if it's good.")
    if os.path.isfile(UNMATCHED_CHOICE_INTERMEDIATE_CSV):
        unmatched_ssa_lines = csv_as_list(UNMATCHED_CHOICE_INTERMEDIATE_CSV)
        print(
            "Found work-in-progress, importing from "
            + UNMATCHED_CHOICE_INTERMEDIATE_CSV
        )
    elif skipped_ciel_auto:
        unmatched_ssa_lines = csv_as_list(UNMATCHED_CIEL_AUTO_CSV)
    print(str(len(unmatched_ssa_lines)) + " SSA drugs left to sort.\n")
    matches, unmatched_ssa_lines = extract_user_chosen_matches(
        unmatched_ssa_lines, hum_csv, ciel_data
    )
    save_matches_and_unmatched(
        matches, unmatched_ssa_lines, MATCHES_CHOICE_CSV, UNMATCHED_CSV
    )


def extract_good_matches_hum(ssa_lines, hum_csv):
    """
     Args:
        ssa_lines (list): [ssa_code, ssa_name, moa, clean_ssa_name]
        hum_csv (list): The HUM_Drug_List CSV file as a list

    Returns:
        matches: [ssa_code, ssa_name, moa, concept_code, clean_hum_name, score]
        unmatched_ssa_lines: The lines from ssa_lines with no match
    """
    # create a dict [concept code -> HUM drug name]
    # this also serves to de-duplicate concept codes
    # {concept_code: clean_hum_name}
    hum_codes_to_drug_names = {l[3]: clean_hum_drug_name(l[2]) for l in hum_csv}

    # [(ssa_code, ssa_name, moa, clean_ssa_name), (hum_name, score, concept_code)]
    matches = [
        (l, process.extractOne(l[3], hum_codes_to_drug_names)) for l in tqdm(ssa_lines)
    ]
    good_matches = [m for m in matches if m[1][1] > HUM_MATCH_SCORE_LIMIT]

    # [ssa_code, ssa_name, moa, concept_code, clean_hum_name, score]
    good_matches_formatted = [
        [m[0][0], m[0][1], m[0][2], m[1][2], m[1][0], m[1][1]] for m in good_matches
    ]

    # [clean_ssa_name]
    matched_clean_ssa_names = [l[0][3] for l in good_matches]
    # [ssa_code, ssa_name, moa, clean_ssa_name]
    ssa_remainder = [l for l in ssa_lines if l[3] not in matched_clean_ssa_names]

    return good_matches_formatted, ssa_remainder


def extract_good_matches_ciel(ssa_lines, ciel_data):
    """
     Args:
        ssa_lines (list): [ssa_code, ssa_name, moa, clean_ssa_name]
        ciel_data (list): The ciel json as a list

    Returns:
        matches: [ssa_code, ssa_name, moa, concept_code, clean_hum_name]
        unmatched_ssa_lines: The lines from ssa_lines with no match
    """
    # { ciel_code: clean_ciel_name }
    ciel_code_to_ciel_name = {
        "CIEL:{}".format(i["id"]): clean_ciel_drug_name(i["display_name"])
        for i in ciel_data
    }

    # [(ssa_code, ssa_name, moa, clean_ssa_name), (clean_ciel_name, score, ciel_code)]
    matches = [
        (
            l,
            process.extractOne(
                l[3], ciel_code_to_ciel_name, scorer=fuzz.token_sort_ratio
            ),
        )
        for l in tqdm(ssa_lines)
    ]
    good_matches = [m for m in matches if m[1][1] > CIEL_MATCH_SCORE_LIMIT]

    # [ssa_code, ssa_name, moa, concept_code, clean_ciel_name, score]
    good_matches_formatted = [
        [m[0][0], m[0][1], m[0][2], m[1][2], m[1][0], m[1][1]] for m in good_matches
    ]

    # [clean_ssa_name]
    matched_clean_ssa_names = [l[0][3] for l in good_matches]
    # [ssa_code, ssa_name, moa, clean_ssa_name]
    ssa_remainder = [l for l in ssa_lines if l[3] not in matched_clean_ssa_names]

    return good_matches_formatted, ssa_remainder


def extract_user_chosen_matches(ssa_lines, hum_csv, ciel_data):
    """
     Args:
        ssa_lines (list): [ssa_code, ssa_name, moa, clean_ssa_name]
        hum_csv (list): The HUM_Drug_List CSV file as a list
        ciel_data (list): The ciel json as a list

    Returns:
        matches: [ssa_code, ssa_name, moa, concept_code, clean_hum_name]
        unmatched_ssa_lines: The lines from ssa_lines with no match
    """
    HUM_MATCH_LIMIT = 2
    CIEL_MATCH_LIMIT = 6
    # create a dict [concept code -> HUM drug name]
    # this also serves to de-duplicate concept codes
    # {concept_code: clean_hum_name}
    hum_codes_to_drug_names = {l[3]: clean_hum_drug_name(l[2]) for l in hum_csv}

    # let's keep another with the full hum_name, for reference
    hum_codes_to_full_drug_names = {l[3]: l[2] for l in hum_csv}

    # { ciel_code: clean_ciel_name }
    ciel_code_to_ciel_name = {
        "CIEL:{}".format(i["id"]): clean_ciel_drug_name(i["display_name"])
        for i in ciel_data
    }

    # [ssa_code, ssa_name, moa, concept_code, clean_other_name]
    choice_matches = []
    for ssa_linenum, ssa_line in enumerate(ssa_lines):
        print(ssa_line[1])
        print("0) None of these")
        hum_matches = process.extract(
            ssa_line[3], hum_codes_to_drug_names, limit=HUM_MATCH_LIMIT
        )
        ciel_sorted_match = process.extractOne(
            ssa_line[3], ciel_code_to_ciel_name, scorer=fuzz.token_sort_ratio
        )
        ciel_matches = process.extract(
            ssa_line[3], ciel_code_to_ciel_name, limit=CIEL_MATCH_LIMIT
        )
        for i, match in enumerate(hum_matches):
            full_hum_name = hum_codes_to_full_drug_names[match[2]]
            print(
                "{}) {}\t({}),\te.g. {}".format(
                    i + 1, match[0], match[2], full_hum_name
                )
            )
        print(
            "{}) {}\t({})".format(
                HUM_MATCH_LIMIT + 1, ciel_sorted_match[0], ciel_sorted_match[2]
            )
        )
        for i, match in enumerate(ciel_matches):
            print(
                "{}) {}\t({})".format(i + 1 + HUM_MATCH_LIMIT + 1, match[0], match[2])
            )
        choice_num = None
        while choice_num is None:
            choice_input = input("Any of these look right? ")
            try:
                choice_num = (
                    int(choice_input) - 1
                )  # the user input numbers are 1-indexed
            except ValueError:
                print("{} is not a valid input. Try again.".format(choice_input))
        choice = None
        if choice_num in range(HUM_MATCH_LIMIT):
            choice = hum_matches[choice_num]
        elif choice_num == HUM_MATCH_LIMIT:
            choice = ciel_sorted_match
        elif choice_num in range(
            HUM_MATCH_LIMIT + 1, HUM_MATCH_LIMIT + 1 + CIEL_MATCH_LIMIT
        ):
            choice = ciel_matches[choice_num - (HUM_MATCH_LIMIT + 1)]
        if choice:
            choice_matches.append(
                [ssa_line[0], ssa_line[1], ssa_line[2], choice[2], choice[0], "-"]
            )
            print("chose {}".format(choice))
            write_to_csv(choice_matches, CHOICE_MATCHES_INTERMEDIATE_CSV)
        print("writing unmatched " + str(len(ssa_lines[ssa_linenum:])))
        write_to_csv(ssa_lines[ssa_linenum + 1 :], UNMATCHED_CHOICE_INTERMEDIATE_CSV)
        print()
    # [clean_ssa_name]
    matched_clean_ssa_names = [l[1] for l in choice_matches]
    # [ssa_code, ssa_name, moa, clean_ssa_name]
    ssa_remainder = [l for l in ssa_lines if l[3] not in matched_clean_ssa_names]
    return choice_matches, ssa_remainder


def save_matches_and_unmatched(
    matches, unmatched_ssa_lines, matches_filename, unmatched_filename
):
    """
     Args:
        matches: [ssa_code, ssa_name, moa, concept_code, clean_hum_name, score]
        unmatched_ssa_lines: [ssa_code, ssa_name, moa, clean_ssa_name]
        suffix: str
    """
    print("Found %d matches:" % len(matches))
    selection = input("Enter 'p' to show these, or anything else to continue")
    if selection == "p":
        for m in matches:
            # ssa_name, other_name, matched_code, score
            print("{}\t=\t{}\t{}\t(score: {})".format(m[1], m[4], m[3], m[5]))
    print("\nThese will be put in file " + matches_filename)
    write_to_csv(matches, matches_filename)
    print("{} drugs remain from the SSA list".format(len(unmatched_ssa_lines)))
    print("Writing a csv of this remainder: " + unmatched_filename)
    write_to_csv(unmatched_ssa_lines, unmatched_filename)


def csv_as_list(filename):
    with open(filename, "rt", encoding="utf8") as csvfile:
        reader = csv.reader(csvfile)
        return list(reader)


def clean_csv_list(input_list):
    """Drops blank lines & the header line"""
    return [l for l in input_list if l != []][1:]


def clean_ciel_drug_name(drug_name):
    return drug_name.lower()


def clean_hum_drug_name(drug_name):
    drug_name = drug_name.lower()
    result = re.split(r",|\d", drug_name)[0].strip()
    return result


def clean_ssa_drug_name(drug_name):
    drug_name = drug_name.lower()
    result = re.split(r",|de|-|\(|\d", drug_name)[0].strip()
    if result == "":
        result = drug_name.split()[0]
        print(
            "WARNING: clean_ssa_drug_name reduced drug name to empty string. Using "
            + result
        )
    return result


def from_json_file(filename):
    with open(filename) as f:
        return json.load(f)


def write_to_csv(data, filename):
    with open(filename, "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)


if __name__ == "__main__":
    main()
