def parse_tax_string(tax_str):
    """Parse an organism label as a taxonomic string."""

    tax_dat = dict(
        level=None,
        name=None,
        path=None
    )

    for sep in ["|", ":", ";"]:
        if sep in tax_str:
            break

    tax_dat['path'] = tax_str.split(sep)

    # Parse the final field
    final_org = tax_dat['path'][-1]

    if '__' not in final_org:
        tax_dat["name"] = final_org
        return tax_dat

    level, name = final_org.split("__", 1)

    level_map = dict(
        sk="superkingdom",
        k="kingdom",
        p="phylum",
        c="class",
        o="order",
        f="family",
        g="genus",
        s="species",
        t="strain"
    )
    if level_map.get(level) is None:
        return tax_dat
    tax_dat["level"] = level_map.get(level)
    tax_dat["name"] = name

    return tax_dat
