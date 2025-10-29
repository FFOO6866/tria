# TRIA AI-BPO Policy Documentation

**Version:** 1.0
**Language:** English
**Last Updated:** October 18, 2025

---

## Overview

This directory contains the official policy documentation for TRIA AI-BPO Solutions. These documents serve as the knowledge base for the RAG (Retrieval-Augmented Generation) system that powers the AI assistant.

---

## Document Index

### 1. TRIA Rules and Policies (v1.0)
**File:** `TRIA_Rules_and_Policies_v1.0.md`
**Purpose:** Comprehensive operational policies and business rules
**Covers:**
- Order processing rules (cutoff times, modifications, cancellations)
- Pricing and payment terms (GST, credit terms, late fees)
- Delivery policies and schedules
- Quality assurance and returns procedures
- Data privacy and PDPA compliance
- Terms and conditions
- Contact information

**Use Cases:**
- Customer inquiries about order policies
- Payment and billing questions
- Delivery schedule information
- Returns and refunds procedures
- Legal and compliance questions

---

### 2. TRIA Product FAQ Handbook (v1.0)
**File:** `TRIA_Product_FAQ_Handbook_v1.0.md`
**Purpose:** Detailed product information and frequently asked questions
**Covers:**
- Pizza boxes (10", 12", 14" specifications)
- Food containers and meal trays
- Packaging materials and liners
- Eco-friendly product options
- Custom printing services
- Minimum order quantities
- Product specifications and safety compliance
- Common customer questions

**Use Cases:**
- Product specifications inquiries
- Pricing questions for specific products
- Material and safety certifications
- Eco-friendly options
- Custom printing capabilities
- Storage and shelf life information

---

### 3. TRIA Escalation Routing Guide (v1.0)
**File:** `TRIA_Escalation_Routing_Guide_v1.0.md`
**Purpose:** Guidelines for when and how to escalate customer issues
**Covers:**
- Four-level escalation framework (AI → CSR → Manager → Director)
- Escalation triggers and criteria
- Response time SLAs for each level
- Authority limits at each level
- Scenario-based routing examples
- Contact information for each level
- Quality monitoring and continuous improvement

**Use Cases:**
- Determining when AI should escalate to human agent
- Urgent order handling
- Complaint resolution procedures
- Complex issue routing
- VIP customer handling
- Crisis management protocols

---

### 4. TRIA Tone and Personality Guide (v1.0)
**File:** `TRIA_Tone_and_Personality_v1.0.md`
**Purpose:** Communication style and brand voice guidelines
**Covers:**
- TRIA brand voice characteristics
- Communication principles and tone guidelines
- Language standards (words to use/avoid)
- Emoji usage guidelines
- Scenario-based communication examples
- Cultural sensitivity (Singapore context)
- Channel-specific guidelines (WhatsApp, email, portal)
- Do's and don'ts
- Example responses for various situations

**Use Cases:**
- Training AI response generation
- CSR communication training
- Ensuring consistent brand voice
- Singapore cultural context awareness
- Channel-appropriate communication
- Handling sensitive situations

---

## Usage Guidelines

### For RAG System Implementation

**Document Chunking:**
- Each section is clearly marked with headers for easy chunking
- Subsections provide granular information retrieval
- Tables and lists are formatted for structured extraction
- Examples are labeled clearly for training purposes

**Metadata Tagging:**
Each document should be tagged with:
- `document_type`: policy, faq, guide, or reference
- `version`: 1.0
- `language`: en
- `topics`: [relevant topic tags]
- `last_updated`: 2025-10-18

**Recommended Chunk Size:**
- Policy sections: 200-500 tokens per chunk
- FAQ Q&A pairs: 100-300 tokens per chunk
- Examples: Keep as complete units (50-200 tokens)
- Tables: Keep complete or by row groups

---

### For AI Assistant Training

**Priority Information:**
1. **High Priority** (must retrieve accurately):
   - Pricing information
   - Delivery schedules and cutoff times
   - Product specifications
   - Escalation criteria
   - Contact information

2. **Medium Priority** (should retrieve when relevant):
   - Policy explanations and reasoning
   - FAQ answers and details
   - Example scenarios
   - Cultural guidelines

3. **Low Priority** (background context):
   - Document control information
   - Training guidelines
   - Quality monitoring processes

---

### For Human Agents

**Quick Reference:**
- Use the **Table of Contents** in each document for fast navigation
- Check the **Quick Reference** sections for at-a-glance information
- Refer to **Example Responses** for communication templates
- Use **Scenario-Based** sections for specific situation handling

**Regular Review:**
- All CSRs should review policies monthly
- New team members should study all four documents during onboarding
- Quarterly refreshers on tone and escalation guidelines

---

## Document Maintenance

### Version Control
- Current version: **1.0** (initial release)
- Next scheduled review: **January 18, 2026**
- Version numbering: `Major.Minor`
  - Major: Significant policy changes, restructuring
  - Minor: Updates, clarifications, additions

### Update Process
1. Identify need for update (customer feedback, new products, policy changes)
2. Draft changes with clear change log
3. Review by relevant stakeholders
4. Approve by Director of Operations
5. Update version number and effective date
6. Communicate changes to team
7. Update RAG system embeddings

### Change Log

**v1.0 (October 18, 2025):**
- Initial release of all four policy documents
- Established baseline policies and guidelines
- Created knowledge base for RAG system

---

## Integration with RAG System

### Retrieval Strategy

**Semantic Search:**
- Use embeddings to find relevant sections based on customer query
- Consider context from conversation history
- Rank results by relevance score

**Keyword Matching:**
- Product codes (SKUs)
- Specific policies (cancellation, delivery, etc.)
- Contact information
- Pricing tiers

**Hybrid Approach:**
- Combine semantic search with keyword matching
- Use metadata filters for document type
- Consider freshness (version/date) in ranking

### Response Generation

**Always Include:**
- Direct answer to customer question
- Supporting details from policy documents
- Specific references (product specs, pricing, etc.)
- Clear next steps or call-to-action

**Tone Matching:**
- Reference `TRIA_Tone_and_Personality_v1.0.md` for style
- Adapt formality based on channel and situation
- Use examples as templates

**Escalation Triggers:**
- Cross-reference `TRIA_Escalation_Routing_Guide_v1.0.md`
- Automatically escalate when criteria are met
- Provide context to human agent

---

## Quality Assurance

### Accuracy Checks
- Pricing and product specifications must be 100% accurate
- Policy information must match current business rules
- Contact information must be up-to-date
- SLA timeframes must be achievable

### Consistency Checks
- Terminology used consistently across all documents
- Cross-references between documents are accurate
- Examples align with policies
- Tone matches brand guidelines

### Completeness Checks
- All customer-facing policies documented
- All products covered in FAQ
- All escalation scenarios addressed
- All communication channels have guidelines

---

## Contact for Policy Questions

**Policy Updates & Clarifications:**
- Email: policies@tria-aibpo.sg
- Escalate to: Operations Manager

**RAG System Integration:**
- Email: tech@tria-aibpo.sg
- Escalate to: Technical Team Lead

**Content Questions:**
- Email: support@tria-aibpo.sg
- Escalate to: Customer Service Manager

---

## Appendix: Document Statistics

| Document | Word Count | Sections | Subsections | Tables | Examples |
|----------|-----------|----------|-------------|--------|----------|
| Rules & Policies | ~6,500 | 8 | 35+ | 3 | 10+ |
| Product FAQ | ~7,000 | 10 | 40+ | 4 | 15+ |
| Escalation Guide | ~7,500 | 10 | 45+ | 5 | 20+ |
| Tone & Personality | ~8,000 | 13 | 50+ | 3 | 25+ |
| **TOTAL** | **~29,000** | **41** | **170+** | **15** | **70+** |

**Estimated RAG Chunks:** 150-200 chunks (at 200-300 tokens per chunk)

---

**Document Control:**
- **Prepared by**: TRIA AI-BPO Operations & Tech Teams
- **Approved by**: Director of Operations
- **Next Review Date**: January 18, 2026
- **Document Location**: doc/policy/en/README.md
