# RFQXpert

RFQXpert is an AI-powered system designed to assist with government RFP (Request for Proposal) analysis and eligibility evaluation. The system uses Google's Gemini AI to analyze RFP requirements and determine if a company meets the eligibility criteria.

## Features

- RFP Analysis: Parse and understand complex RFP documents
- Eligibility Evaluation: Determine if a company meets mandatory requirements
- Requirements Matching: Compare company capabilities against RFP requirements
- Detailed Reporting: Generate structured eligibility assessments with recommendations

## Project Structure

```
RFQXpert/
├── data/
│   ├── processed/         # Processed RFP data
│   └── raw/              # Raw RFP documents
├── src/
│   └── llm_inference/
│       └── evaluation/   # Eligibility evaluation modules
└── .env                  # Environment variables
```

## Prerequisites

- Python 3.12 or higher
- Google Cloud account with Gemini API access
- Valid Gemini API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/RFQXpert.git
cd RFQXpert
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   Create a `.env` file in the root directory with your Gemini API key:

```
GEMINI_API_KEY=your-api-key-here
```

## Usage

1. Prepare your RFP data:

   - Place RFP documents in `data/raw/`
   - Processed RFP data should be in JSON format in `data/processed/`

2. Prepare company data:

   - Create a `companydata.json` file in the `data/` directory with your company's profile

3. Run the eligibility evaluation:

```bash
python src/llm_inference/evaluation/eligilibity_agent.py
```

## Data Format

### RFP Data Format

The RFP data should be in JSON format with the following structure:

```json
{
  "rfpDetails": {
    "rfpNumber": "string",
    "title": "string",
    "issuer": "string",
    "department": "string",
    "address": "string",
    "proposalDueDate": "string"
  },
  "bidderEligibility": {
    "experience": "string",
    "preProposalConference": "string",
    "financialStability": "string",
    "compliance": "string"
  }
  // ... other RFP sections
}
```

### Company Data Format

The company data should be in JSON format with the following structure:

```json
{
  "companyProfile": {
    "name": "string",
    "established": "string",
    "type": "string",
    "location": "string",
    "employees": number,
    "annualRevenue": "string"
  },
  "capabilities": {
    "services": ["string"],
    "industries": ["string"],
    "certifications": ["string"]
  },
  // ... other company information
}
```

## Output Format

The system returns a JSON response with the following structure:

```json
{
  "meets_criteria": boolean,
  "met_requirements": ["string"],
  "unmet_requirements": ["string"],
  "reasons": ["string"],
  "recommendations": ["string"]
}
```

## Error Handling

The system includes comprehensive error handling for:

- API connection issues
- Invalid JSON data
- Missing required fields
- File access problems

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini AI for providing the language model capabilities
- The open-source community for various tools and libraries used in this project
