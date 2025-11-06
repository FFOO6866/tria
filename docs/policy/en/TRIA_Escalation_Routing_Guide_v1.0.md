# TRIA AI-BPO Escalation Routing Guide
**Version:** 1.0
**Effective Date:** October 18, 2025
**Last Updated:** October 18, 2025
**Scope:** Customer Service Operations

---

## Table of Contents
1. [Escalation Framework Overview](#1-escalation-framework-overview)
2. [Escalation Levels](#2-escalation-levels)
3. [When to Escalate](#3-when-to-escalate)
4. [Response Time SLAs](#4-response-time-slas)
5. [Escalation Procedures](#5-escalation-procedures)
6. [Scenario-Based Routing](#6-scenario-based-routing)
7. [Contact Information](#7-contact-information)
8. [Monitoring and Reporting](#8-monitoring-and-reporting)

---

## 1. Escalation Framework Overview

### 1.1 Purpose
This guide defines when and how customer inquiries, issues, and requests should be escalated from AI-powered processing to human agents at appropriate levels.

### 1.2 Guiding Principles
1. **Customer-First**: Escalate whenever AI confidence is low or customer explicitly requests human assistance
2. **Efficiency**: Resolve at the lowest appropriate level to ensure fast resolution
3. **Quality**: Ensure complex issues receive appropriate expertise
4. **Transparency**: Keep customers informed throughout escalation process
5. **Continuous Learning**: Feed escalation insights back to improve AI capabilities

### 1.3 Escalation Philosophy
- **AI handles routine**: Standard orders, common FAQs, status checks
- **Humans handle exceptions**: Complex issues, complaints, unusual requests, relationship management
- **Collaboration**: AI assists humans with data, context, and recommendations

---

## 2. Escalation Levels

### Level 1 (L1): AI Agent - TRIA Virtual Assistant
**Scope:** Automated processing with high confidence

**Capabilities:**
- Standard order processing and confirmation
- Order status inquiries
- Product information and pricing
- Delivery schedule information
- FAQ responses
- Simple order modifications (before processing)
- Account information updates

**Limitations:**
- Cannot make judgment calls on complex issues
- Cannot approve exceptions to policies
- Cannot handle complaints requiring empathy/negotiation
- Cannot provide custom quotes beyond standard pricing

**Handoff Triggers:**
- Low confidence in understanding customer request (<70%)
- Customer explicitly requests human agent
- Issue matches defined escalation scenarios
- Anomaly detected (e.g., order quantity 200% above normal)
- System unable to process request automatically

---

### Level 2 (L2): Customer Service Representative (CSR)
**Scope:** Frontline human support for common issues

**Capabilities:**
- Handle escalations from AI
- Process urgent orders and rush requests
- Approve minor exceptions (up to SGD 500 value)
- Resolve basic complaints and service issues
- Coordinate delivery changes and special requests
- Provide detailed product consultation
- Process returns and replacements (standard cases)
- Troubleshoot payment issues
- Update customer account information

**Authority Limits:**
- Approve discounts up to 10%
- Waive fees up to SGD 100
- Approve order cancellations without fee (within policy)
- Authorize redelivery at no charge (first occurrence)
- Approve order modifications after processing cutoff (simple cases)

**Escalation to L3 Triggers:**
- Issue value exceeds SGD 500
- Customer demands to speak with manager
- Policy exception required beyond CSR authority
- Repeated service failures (3+ incidents same customer)
- Legal or regulatory compliance concerns
- Custom quotations or bulk pricing
- Unable to resolve within 2 hours

**Response SLA:** 30 minutes during business hours

---

### Level 3 (L3): Operations Manager
**Scope:** Complex issues, policy exceptions, relationship management

**Capabilities:**
- All L2 capabilities plus:
- Approve significant exceptions (up to SGD 2,000 value)
- Handle VIP customer accounts
- Resolve escalated complaints and disputes
- Coordinate cross-functional issue resolution
- Make custom pricing decisions (within guidelines)
- Authorize emergency deliveries and special logistics
- Approve product returns outside standard policy
- Handle vendor/supplier coordination issues
- Make operational decisions affecting service delivery

**Authority Limits:**
- Approve discounts up to 25%
- Waive fees up to SGD 500
- Approve custom payment terms (case-by-case)
- Authorize special production runs (minimum quantities apply)
- Approve rush production (subject to capacity)

**Escalation to L4 Triggers:**
- Issue value exceeds SGD 2,000
- Strategic customer relationship at risk
- Legal liability concerns
- Media/PR implications
- Regulatory compliance violations
- Product safety or quality crisis
- Unable to resolve within 4 hours or requires policy change

**Response SLA:** 2 hours during business hours

---

### Level 4 (L4): Director/Senior Management
**Scope:** Strategic decisions, major exceptions, crisis management

**Capabilities:**
- All L3 capabilities plus:
- Final authority on major exceptions
- Strategic customer relationship decisions
- Policy changes and amendments
- Legal and regulatory matters
- Crisis management and public relations
- Major contract negotiations
- High-value custom orders and partnerships

**Authority Limits:**
- Unlimited (within business constraints)
- Can override policies in exceptional circumstances
- Can make strategic pricing decisions
- Can authorize custom product development

**Response SLA:** 4 hours during business hours; 24 hours for strategic matters

---

## 3. When to Escalate

### 3.1 Automatic AI to L2 Escalation (Immediate)

**Order-Related:**
- Urgent order request (keywords: URGENT, ASAP, RUSH, EMERGENCY, SAME-DAY)
- Order quantity anomaly detected (>200% of customer's historical average)
- Order modification requested after processing cutoff
- Cancellation request with penalty involved
- Delivery address outside standard zones
- Order value exceeds customer's credit limit

**Customer Request:**
- Customer types "human", "agent", "speak to someone", "representative"
- Customer expresses frustration or dissatisfaction
- Customer mentions "complaint", "problem", "issue", "disappointed"
- Customer asks for manager or supervisor
- Repeated messages suggesting AI misunderstanding (3+ back-and-forth)

**System Limitations:**
- AI confidence score below 70%
- Unable to parse order details from message
- Product requested not found in catalog
- Payment system error or declined payment
- Customer account status: suspended or flagged

**Quality/Safety:**
- Product quality complaint or defect report
- Food safety concern mentioned
- Customer injury or health issue related to product

---

### 3.2 CSR (L2) to Operations Manager (L3) Escalation

**Value-Based:**
- Issue involves amount greater than SGD 500
- Discount request exceeds 10%
- Fee waiver request exceeds SGD 100
- Custom order value exceeds SGD 2,000

**Complexity:**
- Customer has had 3+ issues in past 90 days
- Issue requires coordination across multiple departments
- Custom product specifications or special production
- Bulk pricing request (>10,000 units)
- Custom payment terms or credit extension

**Customer Relationship:**
- VIP customer (annual spend >SGD 50,000)
- Strategic partnership account
- Customer threatening to switch suppliers
- Customer mentions legal action or regulatory complaint

**Operational:**
- Delivery failure due to internal error (not customer fault)
- Product recall or safety notice
- Inventory shortage affecting multiple customers
- Production delay affecting delivery commitments

---

### 3.3 Operations Manager (L3) to Director (L4) Escalation

**High Stakes:**
- Issue value exceeds SGD 2,000
- Potential legal liability
- Media or public relations implications
- Regulatory compliance violation

**Strategic:**
- Major customer relationship at risk (annual value >SGD 100,000)
- Contract renegotiation or termination
- New product development request
- Partnership or distribution agreement

**Crisis:**
- Product safety recall
- Major quality issue affecting multiple customers
- Supply chain disruption affecting service delivery
- Cybersecurity incident or data breach
- Significant negative social media coverage

---

## 4. Response Time SLAs

### 4.1 Response Time by Level

| Level | Initial Response | Resolution Target | Maximum Resolution Time |
|-------|------------------|-------------------|-------------------------|
| L1 (AI) | Immediate | 5 minutes | 15 minutes |
| L2 (CSR) | 30 minutes | 2 hours | 4 hours |
| L3 (Manager) | 2 hours | 4 hours | 24 hours |
| L4 (Director) | 4 hours | 24 hours | 72 hours |

**Notes:**
- Response times apply during business hours (Monday-Saturday, 8 AM - 6 PM SGT)
- After-hours urgent escalations: On-call manager responds within 1 hour
- Resolution target = 80% of cases resolved within timeframe
- Maximum resolution time = hard deadline for all cases

---

### 4.2 Response Time by Issue Type

| Issue Type | Target Response | Target Resolution |
|------------|-----------------|-------------------|
| Urgent Order | 30 minutes | 2 hours |
| Quality Complaint | 2 hours | 24 hours |
| Delivery Issue | 1 hour | 4 hours |
| Payment Issue | 2 hours | 24 hours |
| Product Inquiry | 1 hour | 2 hours |
| General Complaint | 2 hours | 24 hours |
| Custom Quote | 4 hours | 48 hours |

---

### 4.3 SLA Breach Protocol

**If SLA Will Be Missed:**
1. Notify customer immediately with status update
2. Provide revised timeline and reason for delay
3. Escalate to next level if needed
4. Offer service recovery (discount/credit) if appropriate

**Breach Recording:**
- All SLA breaches logged for analysis
- Monthly review of breach patterns
- Continuous improvement initiatives

---

## 5. Escalation Procedures

### 5.1 AI to CSR (L2) Handoff Process

**Step 1: AI Detection**
- AI identifies escalation trigger
- Captures full conversation context
- Assigns priority level (Urgent/High/Normal)

**Step 2: CSR Notification**
- Real-time alert sent to available CSR
- Context summary provided:
  - Customer name and account info
  - Order history and value
  - Conversation transcript
  - Detected issue/request
  - AI confidence scores

**Step 3: Customer Notification**
"I understand this requires human assistance. I'm connecting you with our customer service representative who will help you shortly. Expected response time: 30 minutes."

**Step 4: CSR Acknowledgment**
- CSR accepts handoff within 5 minutes
- Reviews context
- Responds to customer within SLA

**Step 5: Continuation**
- CSR engages customer via same channel (WhatsApp)
- References previous conversation
- Resolves issue or escalates further if needed

---

### 5.2 CSR to Manager (L3) Handoff Process

**Step 1: CSR Assessment**
- Determines escalation needed based on criteria
- Prepares escalation summary:
  - Issue description
  - Customer impact
  - Action taken so far
  - Recommendation
  - Urgency level

**Step 2: Manager Notification**
- Email + SMS/WhatsApp notification
- Escalation ticket created in system
- Customer timeline updated

**Step 3: Customer Notification (by CSR)**
"I'm escalating this to our Operations Manager [Name] who has the authority to help with this situation. You'll hear from [him/her] within 2 hours."

**Step 4: Manager Response**
- Manager reviews context within 30 minutes
- Contacts CSR if clarification needed
- Responds to customer within SLA

---

### 5.3 Manager to Director (L4) Handoff Process

**Step 1: Manager Assessment**
- Confirms L4 escalation criteria met
- Prepares executive summary:
  - Business impact
  - Recommended action
  - Risk assessment
  - Customer value/relationship context

**Step 2: Director Notification**
- Direct phone call + email
- Executive escalation ticket
- Include financial impact and strategic implications

**Step 3: Customer Notification (by Manager)**
"Given the significance of this matter, I'm bringing in our Director [Name] who will personally review your case and ensure we reach the best resolution. You'll hear from [him/her] within 4 hours."

**Step 4: Director Engagement**
- Director personally contacts customer
- Has full authority to resolve
- May involve other executives if needed (e.g., CEO for strategic accounts)

---

## 6. Scenario-Based Routing

### 6.1 Order Processing Scenarios

#### Scenario: Standard Order
**Customer**: "Hi, I need 600 boxes of 10-inch, 200 boxes of 12-inch, and 400 boxes of 14-inch."
**Routing**: L1 (AI) processes automatically
**Action**: AI extracts quantities, confirms catalog match, calculates total, confirms order

---

#### Scenario: Urgent Order
**Customer**: "URGENT! Need 300 boxes delivered tomorrow!"
**Routing**: L1 → L2 immediately
**Action**:
- AI detects "URGENT" keyword
- Escalates to CSR within 30 seconds
- CSR reviews inventory and delivery capacity
- Confirms feasibility or suggests alternative timeline
- May charge rush fee if applicable

---

#### Scenario: Anomaly Order
**Customer**: "I need 6000 boxes of 10-inch..." (10x normal order)
**Routing**: L1 holds → L2 for confirmation
**Action**:
- AI detects quantity anomaly (>200% of average)
- AI sends confirmation message: "This order is significantly larger than your usual. Can you confirm the quantities?"
- If customer confirms: L2 reviews for fraud/error
- If customer doesn't respond in 2 hours: L2 calls customer directly

---

#### Scenario: Order Modification After Cutoff
**Customer**: "Can I add 200 more boxes to my order placed this morning?"
**Routing**: L1 → L2
**Action**:
- AI checks order status and cutoff time
- If past cutoff: Escalates to L2
- CSR checks if warehouse can accommodate
- Approves if possible; otherwise offers alternatives

---

### 6.2 Quality and Complaint Scenarios

#### Scenario: Defective Product Report
**Customer**: "The boxes we received are damaged. About 50 pieces are crushed."
**Routing**: L1 → L2 immediately
**Action**:
- AI detects quality issue keywords
- Escalates to CSR for immediate handling
- CSR requests photos
- Arranges replacement
- Logs quality incident for analysis
- If >100 pieces or repeated issue: Escalate to L3

---

#### Scenario: Serious Quality Complaint
**Customer**: "We found contamination in the containers. This is a food safety issue!"
**Routing**: L1 → L2 → L3 → L4 immediately
**Action**:
- AI detects food safety keywords
- Immediate escalation to CSR
- CSR immediately escalates to L3 (Manager)
- Manager contacts customer within 15 minutes
- L4 (Director) notified for crisis management
- Product safety team activated
- Potential batch hold or recall initiated

---

#### Scenario: General Complaint
**Customer**: "Not happy with the last delivery. Boxes are not the quality they used to be."
**Routing**: L1 → L2
**Action**:
- AI detects complaint sentiment
- Escalates to CSR
- CSR engages with empathy
- Investigates specific issues
- Offers resolution (replacement, discount, quality assurance)
- If unresolved after 2 hours: Escalate to L3

---

### 6.3 Pricing and Payment Scenarios

#### Scenario: Standard Pricing Inquiry
**Customer**: "How much for 500 pieces of 12-inch boxes?"
**Routing**: L1 (AI) handles
**Action**: AI calculates from catalog (500 x SGD 0.65 = SGD 325 + 8% GST = SGD 351)

---

#### Scenario: Bulk Discount Request
**Customer**: "Can you give us a better price for 20,000 boxes?"
**Routing**: L1 → L2 → L3
**Action**:
- AI recognizes bulk pricing request
- L2 (CSR) provides standard volume discount guidelines
- If customer wants custom quote: L3 (Manager) reviews and quotes
- If strategic account (>SGD 100K annual): May involve L4

---

#### Scenario: Payment Issue
**Customer**: "My payment was declined but I'm sure there are funds."
**Routing**: L1 → L2
**Action**:
- AI detects payment issue
- L2 (CSR) reviews payment details
- CSR troubleshoots (wrong account number, payment method issue)
- Provides alternative payment methods
- If persistent system issue: Escalate to technical support + L3

---

#### Scenario: Credit Extension Request
**Customer**: "Can we extend payment terms to Net 45 this month?"
**Routing**: L1 → L2 → L3
**Action**:
- AI escalates financial request
- L2 reviews customer payment history
- If good standing: L2 may approve one-time 5-day extension
- For longer extension: L3 approval required
- L3 reviews credit risk and approves/denies

---

### 6.4 Delivery Scenarios

#### Scenario: Standard Delivery Inquiry
**Customer**: "When will my order be delivered?"
**Routing**: L1 (AI) handles
**Action**: AI checks order status and delivery schedule, provides ETA

---

#### Scenario: Delivery Address Change
**Customer**: "Can we change delivery address to a different outlet?"
**Routing**:
- If >24 hours before delivery: L1 (AI) processes
- If <24 hours before delivery: L1 → L2
**Action**:
- AI checks timing
- If within policy: AI updates address
- If too close to delivery: CSR coordinates with logistics

---

#### Scenario: Missed Delivery
**Customer**: "Driver never showed up for our scheduled delivery!"
**Routing**: L1 → L2 → L3 (if internal error)
**Action**:
- AI escalates to CSR immediately
- CSR checks delivery status and driver logs
- If driver issue: Reschedule immediately at no charge
- If customer error (wrong address/unavailable): Explain redelivery fee
- If internal error: L3 approves free redelivery + service recovery

---

#### Scenario: Special Delivery Request
**Customer**: "Can you deliver to a new construction site with restricted access?"
**Routing**: L1 → L2
**Action**:
- AI recognizes non-standard delivery
- CSR coordinates with logistics
- Obtains access requirements
- Confirms feasibility and any additional charges

---

### 6.5 Product and Custom Order Scenarios

#### Scenario: Product Availability
**Customer**: "Do you have bagasse containers in stock?"
**Routing**: L1 (AI) handles
**Action**: AI checks catalog and inventory, confirms availability

---

#### Scenario: Custom Product Request
**Customer**: "Can you make 16-inch pizza boxes for us?"
**Routing**: L1 → L2 → L3
**Action**:
- AI recognizes custom product request
- L2 provides information on minimums and lead time
- L3 provides formal quote for custom size production

---

#### Scenario: Custom Printing Quote
**Customer**: "We want our logo printed on 5000 boxes. How much?"
**Routing**: L1 → L2
**Action**:
- AI recognizes custom printing request
- L2 collects details (design, colors, print area)
- L2 provides quote based on standard pricing
- Sends to custom@tria-aibpo.sg for design review

---

## 7. Contact Information

### 7.1 Escalation Contact Directory

#### Level 2: Customer Service Representatives
- **WhatsApp**: +65 XXXX XXXX (monitored 8 AM - 6 PM Mon-Sat)
- **Email**: support@tria-aibpo.sg
- **Phone**: +65 6XXX XXXX (business hours)
- **Response SLA**: 30 minutes

**Current CSR Team:**
- Sarah Tan (Lead CSR) - sarah.tan@tria-aibpo.sg
- Marcus Wong - marcus.wong@tria-aibpo.sg
- Priya Sharma - priya.sharma@tria-aibpo.sg

---

#### Level 3: Operations Manager
- **Email**: operations@tria-aibpo.sg
- **Direct Phone**: +65 9XXX XXXX
- **WhatsApp**: +65 9XXX XXXX (urgent matters)
- **Response SLA**: 2 hours

**Operations Manager:**
- David Lim - david.lim@tria-aibpo.sg
- Backup: Jennifer Ng (Assistant Manager) - jennifer.ng@tria-aibpo.sg

---

#### Level 4: Director
- **Email**: director@tria-aibpo.sg
- **Direct Phone**: +65 9XXX XXXX (strategic matters only)
- **Response SLA**: 4 hours

**Director:**
- Alex Chen, Director of Operations - alex.chen@tria-aibpo.sg

---

### 7.2 After-Hours Emergency Escalation

**Definition of Emergency:**
- Customer operations severely disrupted
- Food safety or health concern
- Major delivery failure affecting event/business
- PR/media crisis

**Emergency Protocol:**
1. Customer sends WhatsApp marked "EMERGENCY"
2. On-call manager receives alert (24/7 rotation)
3. Manager responds within 1 hour
4. Director notified if meets L4 criteria

**On-Call Manager Hotline**: +65 9XXX XXXX (after hours only)

---

### 7.3 Specialized Support Contacts

| Department | Contact | Purpose |
|------------|---------|---------|
| Quality Assurance | quality@tria-aibpo.sg | Defects, product issues |
| Custom Orders | custom@tria-aibpo.sg | Printing, special products |
| Accounts/Billing | accounts@tria-aibpo.sg | Invoices, payments |
| Technical Support | tech@tria-aibpo.sg | Portal, system issues |
| Logistics | logistics@tria-aibpo.sg | Delivery coordination |

---

## 8. Monitoring and Reporting

### 8.1 Escalation Metrics

**Key Performance Indicators (KPIs):**
- Escalation rate (% of interactions escalated)
- Escalation resolution time by level
- SLA compliance rate
- Re-escalation rate (issue returns after resolution)
- Customer satisfaction post-escalation

**Targets:**
- L1 (AI) handles 70% of interactions without escalation
- L2 resolves 80% of escalations without further escalation
- 95% SLA compliance across all levels
- <5% re-escalation rate
- >4.0/5.0 customer satisfaction score

---

### 8.2 Escalation Analysis

**Weekly Review:**
- Escalation volume trends
- Top escalation reasons
- Agent performance
- SLA compliance

**Monthly Review:**
- Root cause analysis of common escalations
- AI training improvements based on escalations
- Process optimization opportunities
- Customer feedback themes

**Quarterly Review:**
- Strategic escalation patterns
- Policy updates needed
- Training requirements
- System improvements

---

### 8.3 Continuous Improvement

**Feedback Loop:**
1. Escalated cases analyzed for AI improvement
2. Common patterns identified
3. AI training data updated
4. Policy clarifications added
5. FAQ expanded
6. Staff training conducted

**Escalation Reduction Goals:**
- Reduce L1→L2 escalations by 5% quarter-over-quarter
- Improve AI confidence scores through training
- Expand AI capabilities to handle more scenarios autonomously
- Reduce average handling time at each level

---

## 9. Training and Quality Assurance

### 9.1 CSR Training Requirements

**Initial Training (2 weeks):**
- Product knowledge
- System navigation
- Escalation criteria
- Conflict resolution
- Empathy and communication skills
- TRIA policies and procedures

**Ongoing Training:**
- Monthly product updates
- Quarterly soft skills refresher
- New process training as needed
- Escalation case studies review

**Certification:**
- All CSRs must pass certification exam
- Annual recertification required
- Specialty certifications (custom orders, technical support)

---

### 9.2 Quality Monitoring

**Call/Chat Monitoring:**
- 10% of interactions randomly sampled
- 100% of escalations to L3+ reviewed
- Weekly feedback sessions
- Monthly performance reviews

**Quality Criteria:**
- Response time compliance
- Resolution quality
- Communication tone and professionalism
- Policy adherence
- Documentation accuracy

**Escalation Quality Score:**
- Correct escalation decision (was escalation needed?)
- Adequate context provided to next level
- Customer kept informed
- SLA met
- Issue resolved at appropriate level

---

## 10. Appendix: Quick Reference

### 10.1 Escalation Decision Tree

```
Customer Interaction
    ↓
AI processes request
    ↓
Can AI handle with >70% confidence?
    ↓ YES → Process automatically (L1)
    ↓ NO
    ↓
Matches auto-escalation criteria?
    ↓ YES → Escalate to L2
    ↓
L2 CSR review
    ↓
Resolved within authority? → YES → Close
    ↓ NO
    ↓
Value >SGD 500 OR Complex issue?
    ↓ YES → Escalate to L3
    ↓
L3 Manager review
    ↓
Resolved within authority? → YES → Close
    ↓ NO
    ↓
Strategic/Legal/Crisis?
    ↓ YES → Escalate to L4
    ↓
L4 Director final resolution
```

---

### 10.2 Quick Escalation Checklist

**Before Escalating to Next Level, Confirm:**
- [ ] Issue exceeds current level authority
- [ ] All available information gathered
- [ ] Escalation context prepared
- [ ] Customer notified of escalation
- [ ] SLA timer started
- [ ] Escalation ticket created
- [ ] Next level notified

---

### 10.3 Customer Communication Templates

**AI to L2 Escalation:**
"I understand this requires specialized assistance. I'm connecting you with our customer service representative [Name] who will help you with this. You can expect a response within 30 minutes."

**L2 to L3 Escalation:**
"Thank you for your patience. I'm escalating this to our Operations Manager [Name] who has the authority to resolve this matter. [He/She] will contact you within 2 hours with a solution."

**L3 to L4 Escalation:**
"I appreciate the importance of this matter to your business. I'm bringing in our Director [Name] who will personally review your case and work with you on the best resolution. You'll hear from [him/her] within 4 hours."

**SLA Extension Notification:**
"I want to update you on the status of your request. Due to [specific reason], we need an additional [timeframe] to provide you with the best resolution. I apologize for the delay and appreciate your patience. I'll personally ensure this is resolved by [new deadline]."

---

**Document Control:**
- **Prepared by**: TRIA AI-BPO Customer Service Team
- **Approved by**: Director of Operations
- **Next Review Date**: January 18, 2026
- **Document Location**: doc/policy/en/TRIA_Escalation_Routing_Guide_v1.0.md
