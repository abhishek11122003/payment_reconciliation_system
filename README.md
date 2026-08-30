# Payment Reconciliation System

A standalone Windows desktop application for comparing a student payment list with a bank/PhonePe statement.

## Inputs

1. Student Excel/CSV.
2. Bank statement PDF.

The student file can use the columns from the supplied sample:

- Student Name
- Roll Number
- Registration Number
- Amount Paid
- Transaction ID of your payment
- Payment Date
- Payment Time
- Paid To
- Screenshot Amount
- Transaction ID

## Output

The program creates:

- Payment Verification
- Genuine Payments
- Invalid Payments
- Needs Review
- Not Found
- Unclaimed Credits
- Duplicate Conflicts
- Summary

## Install

Open PowerShell in this folder:

```powershell
py -m pip install -r requirements.txt
```

## Run

```powershell
py app.py
```

Then select the student Excel file and bank statement PDF.

## Build the Windows app

To create a standalone Windows executable, open PowerShell in this folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The executable is created at `dist\PaymentReconciliation.exe`. It can be copied to another Windows computer without installing Python. By default, reports created by the packaged app are saved in your Documents folder; you can choose another location in the app.

## Important matching principle

The program does not declare a payment genuine from amount alone. It considers transaction ID, amount, sender-name similarity and payment date. Ambiguous cases are placed in REVIEW.

For production use, the matching rules should be tested against several real statements before relying on the result for disciplinary decisions.
