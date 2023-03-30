import pandas as pd


def parse_rebase(uploaded_file):
    """
    Parse the epigenetic data from REBASE.
    Input is an UploadedFile object.
    """

    # Read the file
    lines = uploaded_file.getvalue().decode("utf-8").splitlines()

    # Populate a list with dicts, each entry being an enzyme
    enzymes = list()
    enzyme = dict()

    # Keep track of the recognition sequences which have been detected thus far
    added_rec_seqs = set()

    # Iterate over each line
    for line in lines:

        # If the line is empty
        if len(line) <= 1:

            # Skip it
            continue

        # If the line has a top-level description field
        elif line.startswith("<*"):

            # Skip it
            continue

        # If the line is a field ending
        elif line.startswith("<>"):

            # If the current enzyme has content
            if len(enzyme) > 0:

                # If the recognition sequence is new
                if "rec_seq" in enzyme and enzyme["rec_seq"] not in added_rec_seqs: # noqa

                    # Add it to the list
                    enzymes.append(enzyme)

                    # Record that we've added this recognition sequence
                    added_rec_seqs.add(enzyme["rec_seq"])

            # Start a new blank entry for the next enzyme
            enzyme = dict()

        # If the line contains a key-value pair
        elif line.startswith("<"):

            # Make sure that there is a matching '>'
            assert '>' in line, f"Expected a '>' character in: {line}"

            # Parse the key and value
            key, value = line[1:].rstrip("\n").split(">", 1)

            # Add the key and value to the dict
            if value.isnumeric():
                enzyme[key] = int(value)
            elif value.isdecimal():
                enzyme[key] = float(value)
            else:
                enzyme[key] = value

    # At the end of reading all of the lines
    # If there is a field remaining
    if len(enzyme) > 0:

        # If the recognition sequence is new
        if "rec_seq" in enzyme and enzyme["rec_seq"] not in added_rec_seqs:

            # Add it to the list
            enzymes.append(enzyme)

    # Reformat the list of enzymes as a DataFrame
    df = pd.DataFrame(enzymes)

    # Only keep those records with the `percent_detected` field
    df = df.loc[
        df.percent_detected.notnull()
    ]

    # Any enzyme without a name will be named for its recognition sequence
    df = df.assign(
        enz_name=df.apply(
            lambda r: r['enz_name'] if not pd.isnull(r['enz_name']) else f"Unknown - {r['rec_seq']}", # noqa
            axis=1
        )
    )

    # Add a single combined name to use for the display
    df = df.assign(
        text=df.apply(
            format_rebase_text,
            axis=1
        ),
        type_label=df.apply(
            format_enzyme_type_label,
            axis=1
        )
    )
    return df


def format_rebase_text(r):
    """
    Format the string which contains the complete set of REBASE information.
    """

    return "<br>".join(
        [
            f"{k}: {v}"
            for k, v in r.items()
            if k not in ['organism', 'enzyme_name']
        ]
    )


def format_enzyme_type_label(r: pd.Series):
    """Format the label of each motif from the REBASE TXT file."""

    # If the enzyme type is present
    if pd.notnull(r.get("enz_type")):

        # And the subtype is present
        if pd.notnull(r.get("sub_type")):

            # Make a combined label
            return f"Type {int(r.enz_type)}{r.sub_type}"

        # Without the subtype
        else:
            return f"Type {int(r.enz_type)}"

    # Without any type information
    return "No Type Assigned"
