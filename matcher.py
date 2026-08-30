from difflib import SequenceMatcher
from datetime import datetime
import math


def norm(value):
    if value is None:
        return ""
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def money(value):
    try:
        return round(float(str(value).replace("₹", "").replace(",", "").strip()), 2)
    except Exception:
        return None


def similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def build_student_record(row):
    claimed_id = (
        row.get("Transaction ID of your payment", "")
        or row.get("Transaction ID", "")
    )

    return {
        "Student Name": row.get("Student Name", ""),
        "Roll Number": row.get("Roll Number", ""),
        "Registration Number": row.get("Registration Number", ""),
        "Expected Amount": money(row.get("Amount Paid", "")),
        "Claimed Transaction ID": str(claimed_id).strip(),
        "Payment Date": row.get("Payment Date", ""),
        "Payment Time": row.get("Payment Time", ""),
        "Paid To": row.get("Paid To", ""),
        "Screenshot Amount": money(row.get("Screenshot Amount", "")),
    }


def score_match(student, tx):
    score = 0
    reasons = []

#    sid = norm(student["Claimed Transaction ID"])
#    tid = norm(tx["transaction_id"])
#
#    # Transaction ID
#    if sid and tid and sid == tid:
#        score += 100
#        reasons.append("Exact transaction ID match")

    sid = norm(student["Claimed Transaction ID"])

    bank_transaction_id = norm(tx["transaction_id"])
    bank_utr = norm(tx["utr"])

    # Transaction ID / UTR
    if sid and (
        sid == bank_transaction_id
        or sid == bank_utr
    ):
        score += 100
        reasons.append("Exact transaction ID/UTR match")

    # Amount
    expected = student["Expected Amount"]
    actual = money(tx["amount"])

    if expected is not None and actual is not None:
        if math.isclose(expected, actual, abs_tol=0.01):
            score += 35
            reasons.append("Amount matched")
        else:
            reasons.append("Amount mismatch")

    # Sender name
    name_score = similarity(
        student["Student Name"],
        tx["sender"]
    )

    if name_score >= 0.90:
        score += 30
        reasons.append("Sender name strongly matched")
    elif name_score >= 0.70:
        score += 15
        reasons.append("Sender name partially matched")

    # Payment date
    try:
        sdate = student["Payment Date"]

        if hasattr(sdate, "date"):
            sdate = sdate.date()
        elif sdate:
            sdate = datetime.fromisoformat(
                str(sdate).split()[0]
            ).date()

        if sdate == tx["date"]:
            score += 10
            reasons.append("Payment date matched")

    except Exception:
        pass

    return (
        score,
        "; ".join(reasons)
        if reasons
        else "No matching evidence"
    )


def reconcile(students_df, bank_transactions):

    students = [
        build_student_record(r)
        for r in students_df.to_dict("records")
    ]

    # ============================================================
    # STEP 1
    # Score every possible student -> bank transaction pair
    # ============================================================

    candidates = []

    for si, student in enumerate(students):

        for ti, tx in enumerate(bank_transactions):

            score, reason = score_match(
                student,
                tx
            )

            candidates.append(
                (score, si, ti, reason)
            )

    candidates.sort(
        reverse=True,
        key=lambda x: x[0]
    )

    # ============================================================
    # STEP 2
    # Detect duplicate CLAIMED transaction IDs
    #
    # This happens BEFORE assigning transactions.
    #
    # Example:
    #
    # Sudhanshu  -> T123
    # Padmanabh  -> T123
    #
    # Neither student gets automatic GENUINE status.
    # ============================================================

    claimed_id_students = {}

    for si, student in enumerate(students):

        claimed_id = norm(
            student["Claimed Transaction ID"]
        )

        if claimed_id:

            claimed_id_students.setdefault(
                claimed_id,
                []
            ).append(si)

    duplicate_student_indexes = set()
    duplicate_conflicts = []

    for transaction_id, student_indexes in claimed_id_students.items():

        if len(student_indexes) > 1:

            duplicate_student_indexes.update(
                student_indexes
            )

            names = [
                students[si]["Student Name"]
                for si in student_indexes
            ]

            duplicate_conflicts.append({
                "Transaction ID": transaction_id,
                "Students Claiming It": ", ".join(names),
                "Count": len(names),
                "Action": "Manual investigation required"
            })

    # ============================================================
    # STEP 3
    # Assign transactions normally ONLY to non-duplicate students
    # ============================================================

    assigned_student = {}
    assigned_tx = {}

    for score, si, ti, reason in candidates:

        if score < 65:
            continue

        # IMPORTANT:
        # Duplicate claimants cannot automatically receive
        # the transaction.
        if si in duplicate_student_indexes:
            continue

        if si in assigned_student:
            continue

        if ti in assigned_tx:
            continue

        assigned_student[si] = (
            ti,
            score,
            reason
        )

        assigned_tx[ti] = si

    # ============================================================
    # STEP 4
    # Create verification rows
    # ============================================================

    verification = []

    for si, student in enumerate(students):

        # --------------------------------------------------------
        # DUPLICATE
        # --------------------------------------------------------

        if si in duplicate_student_indexes:

            claimed_id = norm(
                student["Claimed Transaction ID"]
            )

            tx = None
            score = 0
            reason = (
                "Same transaction ID claimed by multiple students"
            )

            # Find the actual bank transaction
            for bank_tx in bank_transactions:

                if (
                    claimed_id
                    and claimed_id
                    == norm(bank_tx["transaction_id"])
                ):

                    tx = bank_tx

                    score, original_reason = score_match(
                        student,
                        bank_tx
                    )

                    reason = (
                        original_reason
                        + "; Same transaction ID claimed "
                        "by multiple students"
                    )

                    break

            status = "DUPLICATE"

        # --------------------------------------------------------
        # NORMAL ASSIGNED TRANSACTION
        # --------------------------------------------------------

        elif si in assigned_student:

            ti, score, reason = assigned_student[si]

            tx = bank_transactions[ti]

            amount_ok = (
                student["Expected Amount"] is not None
                and math.isclose(
                    student["Expected Amount"],
                    money(tx["amount"]),
                    abs_tol=0.01
                )
            )

            #exact_id = (
            #    bool(
            #        norm(
            #            student["Claimed Transaction ID"]
            #        )
            #    )
            #    and
            #    norm(
            #        student["Claimed Transaction ID"]
            #    )
            #    ==
            #    norm(
            #        tx["transaction_id"]
            #    )
            #)

        #    claimed_id = norm(student["Claimed Transaction ID"])
#
        #    exact_id = (
        #        bool(claimed_id)
        #        and (
        #            claimed_id == norm(tx["transaction_id"])
        #            or claimed_id == norm(tx["utr"])
        #        )
        #    )
#
        #    if exact_id and amount_ok:
#
        #        status = "GENUINE"
#
        #    elif amount_ok and score >= 65:
#
        #        status = "GENUINE"
#
        #    elif not amount_ok and score >= 65:
#
        #        status = "INVALID"
#
        #    else:
#
        #        status = "REVIEW"

            claimed_id = norm(student["Claimed Transaction ID"])
            
            exact_id = (
                bool(claimed_id)
                and (
                    claimed_id == norm(tx["transaction_id"])
                    or claimed_id == norm(tx["utr"])
                )
            )
            
            # --------------------------------------------------------
            # STRICT TRANSACTION ID / UTR VERIFICATION
            # --------------------------------------------------------
            
            if exact_id and amount_ok:
                # Transaction ID / UTR matches AND amount matches
                status = "GENUINE"
            
            elif exact_id and not amount_ok:
                # Transaction ID / UTR matches but amount is wrong
                status = "INVALID"
            
            elif not exact_id and amount_ok and score >= 65:
                # Other details strongly match, but Transaction ID / UTR
                # does not match. Never mark this as GENUINE.
                status = "REVIEW"
                reason += "; Transaction ID/UTR mismatch - manual review required"
            
            elif not exact_id and score >= 35:
                # Some matching evidence exists, but Transaction ID / UTR
                # could not be verified.
                status = "REVIEW"
                reason += "; Transaction ID/UTR could not be verified"
            
            else:
                status = "REVIEW"

        # --------------------------------------------------------
        # NOT AUTOMATICALLY ASSIGNED
        # --------------------------------------------------------

        else:

            choices = [
                c
                for c in candidates
                if c[1] == si
            ]

            best = choices[0] if choices else None

            if best and best[0] >= 35:

                ti = best[2]
                score = best[0]
                reason = best[3]

                tx = bank_transactions[ti]

                status = "REVIEW"

            else:

                score = 0
                reason = (
                    "No corresponding bank credit found"
                )

                tx = None

                status = "NOT FOUND"

        # --------------------------------------------------------
        # Build output row
        # --------------------------------------------------------

        row = {
            **student,

            "Bank Date":
                tx["date"] if tx else "",

            "Bank Time":
                tx["time"] if tx else "",

            "Bank Sender":
                tx["sender"] if tx else "",

            "Received Amount":
                tx["amount"] if tx else "",

            "Bank Transaction ID":
                tx["transaction_id"] if tx else "",

            "Bank UTR":
                tx["utr"] if tx else "",

            "Match Score":
                score,

            "Status":
                status,

            "Reason":
                reason,
        }

        verification.append(row)

    # ============================================================
    # STEP 5
    # Separate result categories
    # ============================================================

    genuine = [
        r for r in verification
        if r["Status"] == "GENUINE"
    ]

    invalid = [
        r for r in verification
        if r["Status"] == "INVALID"
    ]

    review = [
        r for r in verification
        if r["Status"] == "REVIEW"
    ]

    not_found = [
        r for r in verification
        if r["Status"] == "NOT FOUND"
    ]

    duplicate_rows = [
        r for r in verification
        if r["Status"] == "DUPLICATE"
    ]

    # ============================================================
    # STEP 6
    # Find unclaimed bank credits
    # ============================================================

    claimed_transaction_indexes = set(
        assigned_tx.keys()
    )

    # Duplicate claimed IDs also count as claimed bank
    # transactions so they don't appear as UNCLAIMED.
    for si in duplicate_student_indexes:

        claimed_id = norm(
            students[si]["Claimed Transaction ID"]
        )

        if claimed_id:

            for ti, tx in enumerate(bank_transactions):

                if (
                    claimed_id
                    == norm(tx["transaction_id"])
                ):

                    claimed_transaction_indexes.add(ti)

    unclaimed = []

    for ti, tx in enumerate(bank_transactions):

        if ti not in claimed_transaction_indexes:

            unclaimed.append({
                "Bank Date": tx["date"],
                "Bank Time": tx["time"],
                "Sender": tx["sender"],
                "Amount": tx["amount"],
                "Transaction ID": tx["transaction_id"],
                "UTR": tx["utr"],
                "Status": "UNCLAIMED",
                "Reason":
                    "No student record was confidently matched"
            })

    # ============================================================
    # STEP 7
    # Summary
    # ============================================================

    expected_total = sum(
        (r["Expected Amount"] or 0)
        for r in students
    )

    received_total = sum(
        (r["Received Amount"] or 0)
        for r in genuine
    )

    summary = {
        "Total student records":
            len(students),

        "Genuine payments":
            len(genuine),

        "Invalid payments":
            len(invalid),

        "Needs review":
            len(review),

        "Not found":
            len(not_found),

        "Duplicate payments":
            len(duplicate_rows),

        "Unclaimed bank credits":
            len(unclaimed),

        "Duplicate/conflict groups":
            len(duplicate_conflicts),

        "Expected total":
            f"₹{expected_total:.2f}",

        "Verified genuine total":
            f"₹{received_total:.2f}",
    }

    return {
        "verification": verification,
        "genuine": genuine,
        "invalid": invalid,
        "review": review,
        "not_found": not_found,
        "unclaimed": unclaimed,
        "duplicates": duplicate_rows,
        "summary": summary,
    }