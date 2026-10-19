# Research Note: Real-World Underwater Defects

## Visual Characteristics in Murky Water

- **Marine Growth/Biofouling:** Appears as irregular, fuzzy patches; often greenish or brown, obscures surface details.
- **Corrosion:** Reddish or orange spots, sometimes with pitting; may be hard to distinguish in low visibility.
- **Coating Damage:** Bright spots or exposed metal; sharp edges, sometimes with peeling or flaking.
- **Cracks:** Thin, dark lines; may be hard to see unless illuminated at an angle.
- **Anode Wear:** Dull, eroded surfaces; loss of metallic shine.
- **Propeller/Chain Damage:** Scratches, dents, or missing material; often visible as bright reflections.

## Challenges

- **Turbidity:** Reduces contrast, blurs edges, and causes color shifts (green/blue cast).
- **Lighting:** Artificial green-light helps, but can mask defects.
- **Marine Snow:** Floating particles obscure features, especially in video.

## Recommendations

- Use CLAHE, green-light simulation, and edge enhancement for preprocessing.
- Augment datasets with simulated turbidity and marine snow.

---

_Add your domain observations and update as you test on real footage._