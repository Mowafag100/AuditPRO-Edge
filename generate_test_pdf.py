from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_vulnerable_contract():
    filename = "vulnerable_test_contract.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica", 12)
    
    text_lines = [
        "CONFIDENTIAL OUTSOURCING AGREEMENT",
        "",
        "1. SCOPE OF WORK: The Contractor will have unrestricted root access to",
        "   all production databases and internal servers without multi-factor authentication.",
        "",
        "2. LIABILITY ESCAPE CLAUSE (The Trap): The Contractor shall NOT be liable",
        "   for any data breaches, ransomware deployment, or data exfiltration caused",
        "   by their staff, even in cases of gross negligence or intentional sabotage.",
        "",
        "3. INTELLECTUAL PROPERTY: All source code, customer data, and patents",
        "   developed during this project shall automatically become the sole property",
        "   of the Contractor, and the Client waives all rights to sue.",
        "",
        "4. HIDDEN TERMINATION FEE: If the Client terminates this contract for any reason,",
        "   the Client agrees to pay a penalty equal to 500% of the total project value",
        "   within 24 hours, without prior written notice.",
        "",
        "5. GOVERNING LAW: This agreement is governed by the laws of an offshore jurisdiction",
        "   where cyber espionage and data theft are not recognized as crimes."
    ]
    
    y = 750
    for line in text_lines:
        c.drawString(50, y, line)
        y -= 20
        
    c.save()
    print(f" [+] Success: {filename} has been created for your security testing!")

if __name__ == "__main__":
    create_vulnerable_contract()
