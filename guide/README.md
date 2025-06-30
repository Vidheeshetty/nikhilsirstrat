# Documentation Index

This directory contains all documentation for the NT-based Trading Platform, organized by category for easy navigation.

## 📁 Directory Structure

```
documentation/
├── README.md                    # This index file
├── architecture/               # System architecture documentation
├── deployment/                 # Deployment and server setup guides
│   └── DEPLOYMENT_QUICK_START.md  # Quick server deployment guide
├── paper-trading/             # Paper trading specific documentation
│   ├── data/                      # Data catalog and readiness docs
│   │   ├── NSER_DATA_READY.md     # NSER catalog data ready notice
│   │   └── DATA_CATALOG.md        # Catalog contents index (auto-generated)
└── testing/                   # Testing framework documentation
```

## 📚 Documentation Categories

### 🏗️ Architecture Documentation
**Location**: `guide/architecture/`

- **[Reporting Architecture](architecture/reporting_architecture.md)** - Overview of the reporting system architecture, data flow, and component interactions
- **[Strategy Runner Architecture](architecture/strategy_runner_architecture.html)** - Detailed architecture of the strategy execution engine

### 🚀 Deployment Documentation
**Location**: `guide/deployment/`

- **[Production Deployment Guide](deployment/PRODUCTION_DEPLOYMENT.md)** - Comprehensive guide for deploying the platform as a production service on dedicated servers, including:
  - Background daemon setup
  - Docker containerization
  - Server configuration
  - Monitoring and alerting
  - Security considerations
  - Backup and recovery

### 📈 Paper Trading Documentation
**Location**: `guide/paper-trading/`

- **[Paper Trading Setup Guide](paper-trading/PAPER_TRADING_SETUP.md)** - Complete setup guide for paper trading infrastructure, including:
  - Broker integration
  - Configuration options
  - Risk management
  - Reporting setup
  - Troubleshooting

### 🧪 Testing Documentation
**Location**: `guide/testing/`

- **[Testing Framework](testing/testing_framework.html)** - Overview of the testing infrastructure, test categories, and testing best practices

## 🔗 Quick Navigation

### Getting Started
1. **New to the platform?** Start with [Paper Trading Setup](paper-trading/PAPER_TRADING_SETUP.md)
2. **Ready for production?** See [Production Deployment Guide](deployment/PRODUCTION_DEPLOYMENT.md)
3. **Understanding the architecture?** Check [Strategy Runner Architecture](architecture/strategy_runner_architecture.html)

### Common Tasks
- **Setting up paper trading**: [Paper Trading Setup](paper-trading/PAPER_TRADING_SETUP.md)
- **Deploying to server**: [Production Deployment](deployment/PRODUCTION_DEPLOYMENT.md)
- **Understanding reports**: [Reporting Architecture](architecture/reporting_architecture.md)
- **Running tests**: [Testing Framework](testing/testing_framework.html)

### Development Resources
- **Architecture patterns**: `guide/architecture/`
- **Testing guidelines**: `guide/testing/`
- **Deployment strategies**: `guide/deployment/`

## 📋 Documentation Standards

### File Naming Convention
- Use descriptive, lowercase names with underscores
- Include appropriate file extensions (.md, .html)
- Group related files in appropriate subdirectories

### Content Guidelines
- Include table of contents for long documents
- Use clear headings and sections
- Provide code examples where applicable
- Include troubleshooting sections
- Keep documentation up to date with code changes

### Cross-References
When referencing other documentation:
- Use relative paths from the documentation root
- Example: `[Setup Guide](paper-trading/PAPER_TRADING_SETUP.md)`
- Always test links after moving files

## 🔄 Maintenance

### Updating Documentation
1. **Code changes**: Update relevant documentation when modifying code
2. **New features**: Add documentation to appropriate category
3. **File moves**: Update all cross-references
4. **Regular review**: Quarterly review for accuracy and completeness

### Adding New Documentation
1. Choose appropriate category folder
2. Follow naming conventions
3. Update this index file
4. Add cross-references as needed
5. Test all links

## 📞 Support

For questions about documentation:
- Check the relevant category first
- Look for troubleshooting sections
- Review architecture documents for system understanding
- Refer to setup guides for configuration issues

---

*Last updated: $(date)*
*Documentation structure version: 2.0* 