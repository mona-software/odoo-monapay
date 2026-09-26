{
    "name": "MONA Pay - Automatic Bank Transfer Confirmation",
    "summary": "Dynamic VietQR bank transfers with automatic webhook confirmation",
    "version": "18.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "author": "The MONA Group",
    "website": "https://monapay.vn",
    "license": "MIT",
    "depends": ["payment", "website_sale"],
    "data": [
        "views/payment_monapay_templates.xml",
        "data/payment_provider_data.xml",
        "views/payment_provider_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_monapay/static/src/js/payment_status.js",
        ],
    },
    "images": [
        "static/description/banner.png",
        "static/description/icon.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

