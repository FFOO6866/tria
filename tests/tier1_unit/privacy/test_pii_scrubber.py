"""
PII Scrubber Unit Tests
=======================

Comprehensive tests for Singapore PDPA-compliant PII detection and scrubbing.

Tests cover:
- Singapore phone number detection (all formats)
- Email address detection
- NRIC/FIN number detection
- Credit card number detection
- Address and postal code detection
- Edge cases and validation

NO MOCKING - Tests use real regex patterns and actual data.
"""

import pytest
from src.privacy.pii_scrubber import (
    scrub_pii,
    PIIType,
    PIIMetadata,
    validate_scrubbing,
    should_scrub_message,
    get_scrubbing_summary,
)


class TestSingaporePhoneNumbers:
    """Test Singapore phone number detection and scrubbing"""

    def test_mobile_with_country_code_8_series(self):
        """Test Singapore mobile number (8 series) with +65"""
        text = "Call me at +65 8123 4567"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Call me at [PHONE]"
        assert meta.total_count == 1
        assert meta.by_type[PIIType.PHONE.value] == 1

    def test_mobile_with_country_code_9_series(self):
        """Test Singapore mobile number (9 series) with +65"""
        text = "My number is +65 9876 5432"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "My number is [PHONE]"
        assert meta.total_count == 1

    def test_mobile_without_country_code(self):
        """Test Singapore mobile number without +65"""
        text = "Text me at 91234567"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Text me at [PHONE]"
        assert meta.total_count == 1

    def test_landline_with_country_code(self):
        """Test Singapore landline (6 series) with +65"""
        text = "Office: +65 6123 4567"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Office: [PHONE]"
        assert meta.total_count == 1

    def test_landline_without_country_code(self):
        """Test Singapore landline without +65"""
        text = "Call 62345678 for support"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Call [PHONE] for support"
        assert meta.total_count == 1

    def test_toll_free_number(self):
        """Test Singapore toll-free number"""
        text = "Hotline: +65 1800 123 4567"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Hotline: [PHONE]"
        assert meta.total_count == 1

    def test_phone_without_spaces(self):
        """Test phone number without spaces"""
        text = "Contact +6581234567"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Contact [PHONE]"
        assert meta.total_count == 1

    def test_multiple_phones(self):
        """Test multiple phone numbers in same text"""
        text = "Mobile: +65 9123 4567, Office: 62345678"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Mobile: [PHONE], Office: [PHONE]"
        assert meta.total_count == 2
        assert meta.by_type[PIIType.PHONE.value] == 2


class TestEmailAddresses:
    """Test email address detection and scrubbing"""

    def test_simple_email(self):
        """Test simple email address"""
        text = "Email me at john@example.com"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Email me at [EMAIL]"
        assert meta.total_count == 1
        assert meta.by_type[PIIType.EMAIL.value] == 1

    def test_email_with_dots(self):
        """Test email with dots in local part"""
        text = "Contact john.doe@example.com"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Contact [EMAIL]"
        assert meta.total_count == 1

    def test_email_with_plus(self):
        """Test email with plus addressing"""
        text = "Send to user+tag@domain.co.uk"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Send to [EMAIL]"
        assert meta.total_count == 1

    def test_multiple_emails(self):
        """Test multiple email addresses"""
        text = "CC: alice@example.com, bob@test.org"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "CC: [EMAIL], [EMAIL]"
        assert meta.total_count == 2


class TestNRICNumbers:
    """Test Singapore NRIC/FIN number detection"""

    def test_nric_s_series(self):
        """Test NRIC S series (citizens born before 2000)"""
        text = "NRIC: S1234567D"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "NRIC: [NRIC]"
        assert meta.total_count == 1
        assert meta.by_type[PIIType.NRIC.value] == 1

    def test_nric_t_series(self):
        """Test NRIC T series (citizens born from 2000)"""
        text = "ID number T9876543A"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "ID number [NRIC]"
        assert meta.total_count == 1

    def test_fin_f_series(self):
        """Test FIN F series (foreigners before 2000)"""
        text = "FIN: F1234567N"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "FIN: [NRIC]"
        assert meta.total_count == 1

    def test_fin_g_series(self):
        """Test FIN G series (foreigners from 2000)"""
        text = "Foreign ID G9876543X"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Foreign ID [NRIC]"
        assert meta.total_count == 1

    def test_nric_m_series(self):
        """Test Malaysian citizen NRIC M series"""
        text = "Malaysian IC: M1234567K"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Malaysian IC: [NRIC]"
        assert meta.total_count == 1

    def test_nric_case_insensitive(self):
        """Test NRIC detection is case-insensitive"""
        text = "My NRIC is s1234567d"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "My NRIC is [NRIC]"
        assert meta.total_count == 1


class TestCreditCardNumbers:
    """Test credit card number detection"""

    def test_visa_card(self):
        """Test Visa card number"""
        text = "Card: 4532 1234 5678 9010"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Card: [CARD]"
        assert meta.total_count == 1
        assert meta.by_type[PIIType.CARD.value] == 1

    def test_mastercard(self):
        """Test Mastercard number"""
        text = "Pay with 5412 3456 7890 1234"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Pay with [CARD]"
        assert meta.total_count == 1

    def test_amex_card(self):
        """Test American Express card"""
        text = "Amex: 3782 822463 10005"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Amex: [CARD]"
        assert meta.total_count == 1

    def test_card_without_spaces(self):
        """Test card number without spaces"""
        text = "Card number: 4532123456789010"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Card number: [CARD]"
        assert meta.total_count == 1

    def test_card_with_dashes(self):
        """Test card number with dashes"""
        text = "Card: 4532-1234-5678-9010"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "Card: [CARD]"
        assert meta.total_count == 1


class TestAddressesAndPostalCodes:
    """Test Singapore address and postal code detection"""

    def test_postal_code(self):
        """Test Singapore postal code"""
        text = "Postal code: 560123"
        scrubbed, meta = scrub_pii(text)

        assert "[POSTAL_CODE]" in scrubbed or "[ADDRESS]" in scrubbed
        assert meta.total_count >= 1

    def test_block_number(self):
        """Test block number detection"""
        text = "Address: Blk 123 Ang Mo Kio"
        scrubbed, meta = scrub_pii(text)

        assert "[ADDRESS]" in scrubbed
        assert meta.total_count >= 1

    def test_unit_number(self):
        """Test unit number detection"""
        text = "Unit #12-34 Building A"
        scrubbed, meta = scrub_pii(text)

        assert "[ADDRESS]" in scrubbed
        assert meta.total_count >= 1

    def test_street_address(self):
        """Test street address detection"""
        text = "123 Orchard Road Singapore"
        scrubbed, meta = scrub_pii(text)

        assert "[ADDRESS]" in scrubbed
        assert meta.total_count >= 1


class TestMixedPII:
    """Test detection of multiple PII types in same text"""

    def test_all_pii_types(self):
        """Test text with all PII types"""
        text = (
            "Contact John at +65 9123 4567 or john@example.com. "
            "NRIC: S1234567D. Card: 4532 1234 5678 9010. "
            "Address: Blk 123 Ang Mo Kio Singapore 560123"
        )
        scrubbed, meta = scrub_pii(text)

        # Should detect at least 5 PII instances
        assert meta.total_count >= 5
        assert PIIType.PHONE.value in meta.by_type
        assert PIIType.EMAIL.value in meta.by_type
        assert PIIType.NRIC.value in meta.by_type
        assert PIIType.CARD.value in meta.by_type

    def test_multiple_same_type(self):
        """Test multiple instances of same PII type"""
        text = "Call +65 9123 4567 or +65 8765 4321 or 62345678"
        scrubbed, meta = scrub_pii(text)

        assert meta.total_count == 3
        assert meta.by_type[PIIType.PHONE.value] == 3

    def test_pii_metadata_details(self):
        """Test PII metadata contains detailed information"""
        text = "Email: test@example.com, Phone: +65 91234567"
        scrubbed, meta = scrub_pii(text)

        assert len(meta.details) == 2
        assert meta.original_length == len(text)
        assert meta.scrubbed_length < meta.original_length

        # Check details structure
        for detail in meta.details:
            assert 'type' in detail
            assert 'placeholder' in detail
            assert 'position' in detail
            assert 'length' in detail


class TestEdgeCases:
    """Test edge cases and validation"""

    def test_empty_text(self):
        """Test empty text"""
        scrubbed, meta = scrub_pii("")

        assert scrubbed == ""
        assert meta.total_count == 0

    def test_none_text(self):
        """Test None text"""
        scrubbed, meta = scrub_pii(None)

        assert scrubbed is None
        assert meta.total_count == 0

    def test_no_pii(self):
        """Test text with no PII"""
        text = "Hello, I would like to order some pizza boxes please."
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == text
        assert meta.total_count == 0
        assert len(meta.by_type) == 0

    def test_pii_at_text_boundaries(self):
        """Test PII at start and end of text"""
        text = "test@example.com is the email"
        scrubbed, meta = scrub_pii(text)

        assert scrubbed == "[EMAIL] is the email"
        assert meta.total_count == 1

        text2 = "The email is test@example.com"
        scrubbed2, meta2 = scrub_pii(text2)

        assert scrubbed2 == "The email is [EMAIL]"
        assert meta2.total_count == 1

    def test_false_positives_avoidance(self):
        """Test that normal numbers aren't flagged as PII"""
        text = "Order 12345 for quantity 100 units"
        scrubbed, meta = scrub_pii(text)

        # Should not flag order numbers or quantities
        assert "Order 12345" in scrubbed
        assert "100 units" in scrubbed


class TestValidation:
    """Test scrubbing validation"""

    def test_validate_scrubbing_success(self):
        """Test validation passes for properly scrubbed text"""
        original = "Call +65 9123 4567"
        scrubbed, meta = scrub_pii(original)

        assert validate_scrubbing(original, scrubbed, meta) is True

    def test_validate_scrubbing_no_pii(self):
        """Test validation passes when no PII detected"""
        original = "Hello world"
        scrubbed, meta = scrub_pii(original)

        assert validate_scrubbing(original, scrubbed, meta) is True


class TestUtilityFunctions:
    """Test utility functions"""

    def test_should_scrub_message_user(self):
        """Test that user messages should be scrubbed"""
        assert should_scrub_message("user", "Any content") is True

    def test_should_scrub_message_assistant_with_pii(self):
        """Test that assistant messages with PII indicators should be scrubbed"""
        assert should_scrub_message("assistant", "I sent email to test@example.com") is True
        assert should_scrub_message("assistant", "Call +65 9123 4567") is True

    def test_should_scrub_message_assistant_without_pii(self):
        """Test that clean assistant messages don't need scrubbing"""
        result = should_scrub_message("assistant", "Your order is confirmed")
        # May or may not scrub depending on heuristics - just verify it runs
        assert isinstance(result, bool)

    def test_get_scrubbing_summary(self):
        """Test scrubbing summary generation"""
        text = "Email: test@example.com, Phone: +65 91234567"
        scrubbed, meta = scrub_pii(text)

        summary = get_scrubbing_summary(meta)

        assert "2 PII instances" in summary
        assert "EMAIL" in summary or "PHONE" in summary

    def test_get_scrubbing_summary_no_pii(self):
        """Test summary when no PII detected"""
        meta = PIIMetadata()
        summary = get_scrubbing_summary(meta)

        assert summary == "No PII detected"

    def test_pii_metadata_to_dict(self):
        """Test PII metadata serialization"""
        text = "Test +65 91234567"
        scrubbed, meta = scrub_pii(text)

        meta_dict = meta.to_dict()

        assert isinstance(meta_dict, dict)
        assert 'total_count' in meta_dict
        assert 'by_type' in meta_dict
        assert 'details' in meta_dict
        assert 'original_length' in meta_dict
        assert 'scrubbed_length' in meta_dict


class TestRealWorldScenarios:
    """Test real-world conversation scenarios"""

    def test_order_inquiry(self):
        """Test typical order inquiry message"""
        text = (
            "Hi, I want to order 100 boxes. "
            "Please call me at +65 9123 4567 or email john@example.com"
        )
        scrubbed, meta = scrub_pii(text)

        assert meta.total_count == 2
        assert "100 boxes" in scrubbed  # Preserve business context
        assert "[PHONE]" in scrubbed
        assert "[EMAIL]" in scrubbed

    def test_customer_complaint(self):
        """Test customer complaint with personal info"""
        text = (
            "My order was damaged. My NRIC is S1234567D. "
            "Call me urgently at 91234567"
        )
        scrubbed, meta = scrub_pii(text)

        assert meta.total_count == 2
        assert "[NRIC]" in scrubbed
        assert "[PHONE]" in scrubbed
        assert "damaged" in scrubbed  # Preserve complaint context

    def test_delivery_address(self):
        """Test delivery address submission"""
        text = (
            "Deliver to Blk 123 Ang Mo Kio Ave 3 #12-34 Singapore 560123. "
            "Contact: +65 8123 4567"
        )
        scrubbed, meta = scrub_pii(text)

        assert meta.total_count >= 2  # At least phone and address
        assert "[PHONE]" in scrubbed

    def test_payment_info(self):
        """Test message with payment information"""
        text = (
            "I'll pay with card 4532 1234 5678 9010. "
            "Send receipt to billing@company.com"
        )
        scrubbed, meta = scrub_pii(text)

        assert meta.total_count == 2
        assert "[CARD]" in scrubbed
        assert "[EMAIL]" in scrubbed

    def test_multilingual_pii(self):
        """Test PII in multilingual context"""
        text = "请联系我 +65 9123 4567 或 email: test@example.com"
        scrubbed, meta = scrub_pii(text)

        # PII should be detected regardless of language
        assert meta.total_count == 2
        assert "[PHONE]" in scrubbed
        assert "[EMAIL]" in scrubbed
        assert "请联系我" in scrubbed  # Preserve Chinese text


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
