# BeyondBinary

BeyondBinary is a multi-dimensional media credibility and political bias analysis system. It combines natural language inference (NLI), semantic retrieval, and domain-level knowledge bases to evaluate the factual accuracy and ideological framing of news articles.

## ℹ️ Information
BeyondBinary helps users navigate the complex media landscape by decomposing articles into individual factual claims, verifying those claims against authoritative evidence, and analyzing the linguistic and systemic bias of the reporting.

## 🤖 Model Architecture

The system utilizes a modular AI pipeline where specific models are chosen for their strength in either extraction, verification, or classification.

| Module | Model | Purpose |
| :--- | :--- | :--- |
| **Claim Extractor** | `ClaimBuster-DeBERTaV2` | Identifies and extracts check-worthy factual claims from raw article text. |
| **Verifier (NLI)** | `RoBERTa-large-MNLI` | Performs Natural Language Inference to determine if evidence *entails*, *contradicts*, or is *neutral* toward a claim. |
| **Verifier (Embedding)** | `all-MiniLM-L6-v2` | Generates semantic embeddings for efficient retrieval of evidence via FAISS. |
| **Bias Detector** | `mbzuai-political-bias-bert` | A fine-tuned BERT model that classifies the political stance (Left, Center, Right) of the text. |
| **Search Provider** | `Brave Search API` | Provides real-time, authoritative web evidence for claim verification. |
| **Knowledge Base** | `AllSides Ratings` | Provides ground-truth political bias ratings for known media domains. |

## 🧮 Metrics & Formulas

### 1. Credibility Score
The overall credibility of an article is a weighted average of the verdicts of its extracted claims, calibrated by the model's confidence.

**Formula:**
$$\text{Credibility Score} = \left( \frac{\sum (\text{Weight}_{\text{verdict}} \times \text{Confidence})}{\sum \text{Confidence}} \right) \times 100$$

**Variable Definitions:**
- $\text{Weight}_{\text{verdict}}$: A constant assigned based on the NLI outcome:
  - `Supported`: 1.0
  - `Not Enough Info`: 0.5
  - `Misleading-Framing`: 0.35
  - `Refuted`: 0.0
- $\text{Confidence}$: The softmax probability score produced by the **RoBERTa-large-MNLI** model for the winning label.

---

### 2. Bias Spectrum Score
The bias score represents the ideological leaning of the content on a scale from -1.0 (Far Left) to +1.0 (Far Right).

**Formula:**
$$\text{Spectrum Score} = (0.6 \times \text{Domain Score}) + (0.4 \times \text{NLP Score})$$
*(Note: If domain info is unavailable, the score defaults to the NLP Score)*

**Variable Definitions:**
- $\text{Domain Score}$: The numerical bias rating retrieved from the **AllSides Knowledge Base**.
- $\text{NLP Score}$: Calculated as $(P_{\text{right}} \times 1.0) + (P_{\text{left}} \times -1.0)$, where $P$ is the probability assigned by the **mbzuai-political-bias-bert** model.

---

### 3. Loaded Language Density
Measures the prevalence of sensationalist or pejorative terms.

**Formula:**
$$\text{Density \%} = \left( \frac{\text{Count of Loaded Words}}{\text{Total Word Count}} \right) \times 100$$

**Variable Definitions:**
- $\text{Count of Loaded Words}$: The number of matches found between the article text and the **Curated Loaded-Language Lexicon**.
- $\text{Total Word Count}$: The total number of tokens extracted from the text.

## ⚙️ Pipeline

The BeyondBinary pipeline follows a sequential flow to transform a URL or text into a comprehensive analysis report:

1. **Ingestion**: 
   - Fetches raw HTML from a URL.
   - Cleans the content to extract the primary article text.
2. **Claim Extraction**: 
   - The `ClaimBuster` model scans the text and identifies a set of factual assertions.
3. **Evidence Retrieval**: 
   - The system searches a local **FAISS Index** for existing knowledge.
   - If local confidence is low, it queries the **Brave Search API** for real-time web evidence.
4. **Verification (NLI)**: 
   - The `RoBERTa-large-MNLI` model compares the claim against the retrieved evidence.
   - A verdict is assigned: `Supported`, `Refuted`, or `Not Enough Info`.
5. **Framing Analysis**: 
   - The system checks for "Loaded Language" and "Contested Evidence" to determine if a claim is `Misleading-Framing`.
6. **Bias Analysis**: 
   - Combines the publisher's historical bias (AllSides) with a real-time linguistic analysis of the text.
7. **Aggregation**: 
   - Calculates the final **Credibility Score** and **Bias Label** to produce the final output.
