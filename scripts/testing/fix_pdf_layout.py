import re

file_path = r"app\pdf_report.py"

print("Reading pdf_report.py...")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The section to replace (lines 105-124)
old_code = '''        # Original image
        if r["orig_img"] is not None:
            story.append(Paragraph("Original Image", ST["h3"]))
            story.append(_pil_to_rl(r["orig_img"], usable_w, 60*mm))
            story.append(Spacer(1, 4))
        # Enhanced image
        if r["enhanced_img"] is not None:
            story.append(Paragraph("Enhanced Image", ST["h3"]))
            story.append(_pil_to_rl(r["enhanced_img"], usable_w, 60*mm))
            story.append(Spacer(1, 4))
        # Annotated image
        if r["annotated_img"] is not None:
            story.append(Paragraph("Annotated Image", ST["h3"]))
            story.append(_pil_to_rl(r["annotated_img"], usable_w, 60*mm))
            story.append(Spacer(1, 4))
        # Heatmap
        if r["heatmap_img"] is not None:
            story.append(Paragraph("Heatmap", ST["h3"]))
            story.append(_pil_to_rl(r["heatmap_img"], usable_w, 40*mm))
            story.append(Spacer(1, 4))'''

new_code = '''        # 2x2 Image Grid: Original | Enhanced / Annotated | Heatmap
        img_w = (usable_w - 8*mm) / 2  # Split width with gap
        img_h = 55*mm
        
        row1 = []
        row2 = []
        
        # Row 1: Original (left), Enhanced (right)
        if r["orig_img"] is not None:
            img_cell = [
                Paragraph("Original Image", ST["h3"]),
                _pil_to_rl(r["orig_img"], img_w, img_h)
            ]
            row1.append(img_cell)
        else:
            row1.append([Paragraph("", ST["body"])])
            
        if r["enhanced_img"] is not None:
            img_cell = [
                Paragraph("Enhanced Image", ST["h3"]),
                _pil_to_rl(r["enhanced_img"], img_w, img_h)
            ]
            row1.append(img_cell)
        else:
            row1.append([Paragraph("", ST["body"])])
        
        # Row 2: Annotated (left), Heatmap (right)
        if r["annotated_img"] is not None:
            img_cell = [
                Paragraph("Annotated Image", ST["h3"]),
                _pil_to_rl(r["annotated_img"], img_w, img_h)
            ]
            row2.append(img_cell)
        else:
            row2.append([Paragraph("", ST["body"])])
            
        if r["heatmap_img"] is not None:
            img_cell = [
                Paragraph("Heatmap", ST["h3"]),
                _pil_to_rl(r["heatmap_img"], img_w, img_h)
            ]
            row2.append(img_cell)
        else:
            row2.append([Paragraph("", ST["body"])])
        
        # Build the 2x2 grid table
        grid = Table([row1, row2], colWidths=[img_w, img_w], rowHeights=[img_h + 15*mm, img_h + 15*mm])
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4*mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4*mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2*mm),
        ]))
        story.append(grid)
        story.append(Spacer(1, 8))'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✓ Found and replaced image layout code")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Saved changes to pdf_report.py")
    print("\nDone! Generate a new PDF to see the centered 2x2 grid layout.")
else:
    print("❌ Could not find the exact pattern.")
    print("The code may have changed. Please check manually.")

input("\nPress Enter to close...")