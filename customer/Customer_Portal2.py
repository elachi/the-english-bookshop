def generate_apple_pkpass(customer_name, customer_mobile, current_stamps):
    """Generates a signed Apple Wallet .pkpass byte stream using py-pkpass safely."""
    if not APPLE_PASS_AVAILABLE:
        return None
    try:
        passfile = Pass(
            passTypeIdentifier="pass.com.cafetarnan.loyalty",
            teamIdentifier="YOUR_APPLE_TEAM_ID",
            organizationName="Café Tärnan",
            description="Café Tärnan Loyalty Pass"
        )
        passfile.serial_number = str(customer_mobile)
        passfile.backgroundColor = "rgb(48, 112, 65)"
        passfile.foregroundColor = "rgb(255, 255, 255)"
        
        passfile.barcode = Barcode(
            message=str(customer_mobile),
            format=BarcodeFormat.CODE128,
            altText=str(customer_mobile)
        )
        
        passfile.addPrimaryField('customer_name', customer_name, 'CARDHOLDER')
        passfile.addSecondaryField('stamps', f"{current_stamps} / 9", 'STAMPS')
        
        # Uncomment and configure once .pem files are added to your repository:
        # pass_bytes = passfile.create('certificate.pem', 'private.key', 'wwdr.pem')
        # return pass_bytes
        return None
    except Exception as e:
        return None