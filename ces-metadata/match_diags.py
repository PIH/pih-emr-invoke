#! env/bin/python3
"""
match_diags.py

Attempts to match diagnoses from SSA (Mexican MoH) diagnosis list with
those in the PIH concepts server (icd-pih.csv) and, secondarily, CIEL
(icd-ciel.csv).
"""
import csv
import json

SSA_CSV = "./input/diagnoses/ssa-diagnoses.csv"
PIH_CSV = "./input/diagnoses/pih-diagnoses.csv"
PIH_MATCHES_CSV = "./output/diagnoses-matches-pih.csv"
CIEL_CSV = "./input/diagnoses/ciel-diagnoses.csv"
CIEL_MATCHES_CSV = "./output/diagnoses-matches-ciel.csv"
OCL_JSON = "./input/diagnoses/who-diagnoses.json"
UNMATCHED_CSV = "./output/diagnoses-unmatched.csv"


def main():
    ssa_data = clean_csv_list(csv_as_list(SSA_CSV))

    pih_data = clean_csv_list(csv_as_list(PIH_CSV))
    pih_id_to_ssa_name, unmatched_ssa_data = match_on_icd_code(ssa_data, pih_data)
    print("Found {} matches from PIH concepts".format(len(pih_id_to_ssa_name)))
    print(str(len(unmatched_ssa_data)) + " unmatched")
    write_to_csv(pih_id_to_ssa_name, PIH_MATCHES_CSV)

    ciel_data = clean_csv_list(csv_as_list(CIEL_CSV))
    ciel_id_to_ssa_name, unmatched_ssa_data = match_on_icd_code(
        unmatched_ssa_data, ciel_data
    )
    print("Found {} matches from CIEL concepts".format(len(ciel_id_to_ssa_name)))
    print(str(len(unmatched_ssa_data)) + " unmatched")
    write_to_csv(ciel_id_to_ssa_name, CIEL_MATCHES_CSV)

    ocl_data = from_json_file(OCL_JSON)
    formatted_ocl_data = [
        (l["from_concept_code"], l["to_concept_code"]) for l in ocl_data
    ]
    ocl_ciel_id_and_ssa_name, unmatched_ssa_data = match_on_icd_code(
        unmatched_ssa_data, formatted_ocl_data
    )
    print(
        "Found {} matches from OCL CIEL concepts".format(len(ocl_ciel_id_and_ssa_name))
    )
    print(str(len(unmatched_ssa_data)) + " unmatched")
    write_to_csv(ocl_ciel_id_and_ssa_name, CIEL_MATCHES_CSV)

    write_to_csv(unmatched_ssa_data, UNMATCHED_CSV)


def match_on_icd_code(ssa_data, concept_data):
    """
    Args:
        ssa_data (list): data from the CSV file
        concept_data (list): (concept_id, icd_code) from PIH or CIEL
        
    Returns:
        matches (list[tuple]): (concept_id, ssa_name) tuples
        unmatched_ssa (list): entries from ssa_data which were not matched
    """
    icd_code_to_ssa_name = {fix_ssa_icd_code(l[2]): l[4] for l in ssa_data}

    # Put concept_data into a dict, which will de-duplicate on ICD code
    icd_code_to_concept_id = {l[1]: l[0] for l in concept_data}

    concept_id_and_ssa_name = [
        (c[1], icd_code_to_ssa_name[c[0]])
        for c in icd_code_to_concept_id.items()
        if c[0] in icd_code_to_ssa_name
    ]
    selected_concept_ids = [l[0] for l in concept_id_and_ssa_name]
    selected_icd_codes = [
        k for k, v in icd_code_to_concept_id.items() if v in selected_concept_ids
    ]
    unmatched = [
        l for l in ssa_data if fix_ssa_icd_code(l[2]) not in selected_icd_codes
    ]
    return concept_id_and_ssa_name, unmatched


def print_dict_items(data, limit):
    print([[k, v] for k, v in data.items()][:limit])


def csv_as_list(filename):
    with open(filename, "rt", encoding="utf8") as csvfile:
        reader = csv.reader(csvfile)
        return list(reader)


def clean_csv_list(input_list):
    """Drops blank lines & the header line"""
    return [l for l in input_list if l != []][1:]


def from_json_file(filename):
    with open(filename) as f:
        return json.load(f)


def fix_ssa_icd_code(code):
    if len(code) == 3:
        return code
    else:
        if len(code) > 4:
            print("Weird SSA ICD code: " + code)
        return code[:3] + "." + code[3:]


def write_to_csv(data, filename):
    with open(filename, "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)


if __name__ == "__main__":
    main()
