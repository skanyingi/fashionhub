from io import BytesIO


def generate_receipt_pdf(order):
    """Generates PDF receipt for an order"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
            HRFlowable,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        # create buffer to store PDF in memory instead of savid to disk
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()

        # Defines custom paragraph style for the PDF sections
        title_style = ParagraphStyle("Title", fontSize=28, textColor=colors.HexColor("#04AA6D"), alignment=1, spaceAfter=10, fontName="Helvetica-Bold")
        success_style = ParagraphStyle("Success", fontSize=18, textColor=colors.black, alignment=1, spaceAfter=5, fontName="Helvetica-Bold")
        subtitle_style = ParagraphStyle("Subtitle", fontSize=12, textColor=colors.grey, alignment=1, spaceAfter=25)
        section_header = ParagraphStyle("SectionHeader", fontSize=10, textColor=colors.HexColor("#333333"), fontName="Helvetica-Bold", spaceAfter=8, leading=12)
        normal_text = ParagraphStyle("NormalText", fontSize=10, textColor=colors.HexColor("#555555"), leading=14)

        # Adding  my Header payment success at top
        elements.append(Paragraph("FASHIONHUB", title_style))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("Payment Successful!", success_style))
        elements.append(Spacer(1, 0.05 * inch))
        elements.append(Paragraph("Thank you for your purchase. Your order is being processed.", subtitle_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # build a two column info box to show order details ans shipping address side by side
        transaction = order.transactions.filter(status="SUCCESS").order_by("-created_at").first()
        receipt_num = transaction.mpesa_receipt_number if transaction else 'N/A'
        
        info_data = [
            [
                Paragraph("<b>ORDER DETAILS</b>", section_header),
                Paragraph("<b>SHIPPING TO</b>", section_header)
            ],
            [
                Paragraph(f"Order Number: <b>{order.tracking_number}</b><br/>M-Pesa Receipt: <b>{receipt_num}</b><br/>Date: {order.created_at.strftime('%b %d, %Y %H:%M')}<br/>Status: <font color='#04AA6D'><b>PAID</b></font>", normal_text),
                Paragraph(f"Customer: <b>{order.buyer.username if order.buyer else (order.email or 'Guest')}</b><br/>Email: {order.email or (order.buyer.email if order.buyer else 'N/A')}<br/>Phone: {order.phone or 'N/A'}<br/>Location: {order.location or 'N/A'}<br/>Address: {order.address or 'N/A'}", normal_text)
            ]
        ]
        
        info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f9f9f9")),
            ("TOPPADDING", (0,0), (-1,-1), 15),
            ("BOTTOMPADDING", (0,0), (-1,-1), 15),
            ("LEFTPADDING", (0,0), (-1,-1), 15),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#eeeeee")),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.4 * inch))

        # build items purchased table listing each product, size, quantity and total
        elements.append(Paragraph("ITEMS PURCHASED", section_header))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#eeeeee"), spaceAfter=10))

        items_data = [["Product", "Size", "Qty", "Total"]]
        for item in order.items.all():
            items_data.append([
                item.product.name,
                item.size or "N/A",
                str(item.quantity),
                f"KES {item.get_total()}"
            ])

        items_table = Table(items_data, colWidths=[3.8*inch, 1*inch, 0.8*inch, 1.4*inch])
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fdfdfd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#888888")),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.3 * inch))

        # build total section which shows subtotal, delivery_fee and grand total
        totals_data = [
            ["Subtotal:", f"KES {order.get_total_amount()}"],
            ["Delivery Fee:", f"KES {order.delivery_fee or 0}"],
            ["Grand Total:", f"KES {order.get_grand_total()}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[5.6*inch, 1.4*inch])
        totals_table.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "RIGHT"),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
            ("FONTSIZE", (0, 2), (-1, 2), 16),
            ("TEXTCOLOR", (1, 2), (1, 2), colors.HexColor("#04AA6D")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#eeeeee")),
        ]))
        elements.append(totals_table)

        # Add Footer with delivery info and copyright
        elements.append(Spacer(1, 1.5 * inch))
        footer_style = ParagraphStyle("Footer", fontSize=9, textColor=colors.grey, alignment=1, leading=12)
        elements.append(Paragraph("A copy of this receipt has been sent to your email.<br/>Your order will be delivered within 1-2 days.<br/>Thank you for shopping with <b>FashionHub</b>!<br/>© 2026 FashionHub. All rights reserved.", footer_style))

        # Build and return PDF buffer
        doc.build(elements)
        buffer.seek(0)
        return buffer
    # Catch pdf generation errors
    except Exception as e:
        print(f"PDF generation error: {e}")
        return None



