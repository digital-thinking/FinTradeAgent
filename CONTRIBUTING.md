# Contributing to FinTradeAgent

Thank you for your interest in contributing to FinTradeAgent! This document provides guidelines and information for contributors to help maintain a high-quality, collaborative project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [How to Contribute](#how-to-contribute)
4. [Development Guidelines](#development-guidelines)
5. [Pull Request Process](#pull-request-process)
6. [Issue Reporting](#issue-reporting)
7. [Community](#community)

## Code of Conduct

### Our Pledge

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to a positive environment:

- **Being respectful**: Treat all community members with respect and kindness
- **Being collaborative**: Work together constructively and be open to feedback
- **Being inclusive**: Welcome newcomers and help them get started
- **Focusing on what is best for the community**: Make decisions that benefit the project and its users
- **Showing empathy**: Be understanding of different perspectives and experiences

Examples of unacceptable behavior:

- Harassment, intimidation, or discrimination of any kind
- Offensive, derogatory, or inappropriate comments
- Personal attacks or insults
- Publishing private information without permission
- Any conduct that would be inappropriate in a professional setting

### Enforcement

Project maintainers are responsible for clarifying standards and will take appropriate corrective action in response to unacceptable behavior. This may include temporary or permanent removal from project participation.

## Getting Started

### Development Environment

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/FinTradeAgent.git
   cd FinTradeAgent
   ```

2. **Set Up Development Environment**:
   Follow the detailed setup instructions in the [Developer Guide](docs/DEVELOPER_GUIDE.md#development-environment-setup).

3. **Verify Installation**:
   ```bash
   # Backend
   poetry run pytest

   # Frontend
   cd frontend
   npm run test

   # Integration
   docker-compose -f docker-compose.dev.yml up -d
   ```

### Project Structure

Familiarize yourself with the project structure:

- **`backend/`**: FastAPI backend with Python services
- **`frontend/`**: Vue.js frontend application
- **`docs/`**: Comprehensive project documentation
- **`tests/`**: Test suites for all components
- **`scripts/`**: Development and deployment scripts

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

#### 🐛 Bug Fixes
- Report bugs through GitHub Issues
- Fix existing bugs with clear pull requests
- Include regression tests to prevent future issues

#### ✨ New Features
- Discuss major features in GitHub Discussions first
- Start with a GitHub Issue describing the feature
- Follow the feature development process in our [Developer Guide](docs/DEVELOPER_GUIDE.md)

#### 📖 Documentation
- Improve existing documentation
- Add missing documentation
- Fix typos and clarify confusing sections
- Translate documentation (future goal)

#### 🧪 Testing
- Add test coverage for existing code
- Improve test quality and reliability
- Add integration and E2E tests
- Performance testing and benchmarks

#### 🎨 UI/UX Improvements
- Enhance user interface design
- Improve user experience flows
- Add accessibility features
- Mobile responsiveness improvements

#### 🔧 Infrastructure & DevOps
- Improve CI/CD pipelines
- Enhance Docker configurations
- Optimize build processes
- Monitoring and observability improvements

### Contribution Workflow

1. **Check Existing Issues**: Look for existing issues or discussions related to your contribution
2. **Create an Issue**: If none exists, create a new issue describing your intended contribution
3. **Fork the Repository**: Create your own fork of the project
4. **Create a Feature Branch**: Use a descriptive branch name (`feature/add-websocket-support`)
5. **Make Changes**: Implement your changes following our coding standards
6. **Write Tests**: Ensure adequate test coverage for your changes
7. **Update Documentation**: Update relevant documentation
8. **Submit Pull Request**: Create a PR with a clear description of your changes

## Development Guidelines

### Coding Standards

#### Python Backend

**Style Guidelines**:
- Follow PEP 8 style guide
- Use Black for code formatting
- Use type hints for all function signatures
- Maximum line length: 88 characters

**Code Quality Tools**:
```bash
# Format code
poetry run black backend/

# Sort imports
poetry run isort backend/

# Type checking
poetry run mypy backend/

# Linting
poetry run pylint backend/
```

**Example Code Style**:
```python
from typing import List, Optional
import asyncio

async def get_portfolio_data(
    portfolio_name: str, 
    include_holdings: bool = True
) -> Optional[PortfolioData]:
    """Retrieve portfolio data with optional holdings information.
    
    Args:
        portfolio_name: Name of the portfolio to retrieve
        include_holdings: Whether to include detailed holdings data
        
    Returns:
        Portfolio data or None if not found
        
    Raises:
        ValidationError: If portfolio_name is invalid
        DatabaseError: If database query fails
    """
    if not portfolio_name or not portfolio_name.strip():
        raise ValidationError("Portfolio name cannot be empty")
    
    try:
        data = await portfolio_service.get_data(
            name=portfolio_name,
            include_holdings=include_holdings
        )
        return data
    except DatabaseError as e:
        logger.error(f"Failed to retrieve portfolio {portfolio_name}: {e}")
        raise
```

#### Vue.js Frontend

**Style Guidelines**:
- Use Vue 3 Composition API
- Use TypeScript where beneficial
- Follow Vue.js style guide
- Use ESLint and Prettier for consistency

**Code Quality Tools**:
```bash
cd frontend

# Linting
npm run lint

# Fix lint issues
npm run lint:fix

# Type checking (if using TypeScript)
npm run type-check
```

**Example Component Style**:
```vue
<template>
  <div class="portfolio-card">
    <div class="portfolio-header">
      <h3 class="portfolio-name">{{ portfolio.name }}</h3>
      <span 
        class="portfolio-return"
        :class="returnClass"
      >
        {{ formatPercentage(portfolio.returnPct) }}
      </span>
    </div>
    
    <div class="portfolio-metrics">
      <div class="metric">
        <span class="metric-label">Total Value</span>
        <span class="metric-value">{{ formatCurrency(portfolio.totalValue) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatCurrency, formatPercentage } from '@/utils/formatters'

interface Portfolio {
  name: string
  totalValue: number
  returnPct: number
}

const props = defineProps<{
  portfolio: Portfolio
}>()

const returnClass = computed(() => ({
  'text-green-500': props.portfolio.returnPct > 0,
  'text-red-500': props.portfolio.returnPct < 0,
  'text-gray-500': props.portfolio.returnPct === 0
}))
</script>

<style scoped>
.portfolio-card {
  @apply bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow;
}

.portfolio-header {
  @apply flex justify-between items-center mb-4;
}

.portfolio-name {
  @apply text-xl font-semibold text-gray-900;
}
</style>
```

### Testing Requirements

#### Backend Testing

**Test Coverage**: Aim for >80% code coverage
**Test Types**:
- Unit tests for individual functions/methods
- Integration tests for API endpoints
- End-to-end tests for complete workflows

```python
# tests/test_portfolio_service.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.services.portfolio_service import PortfolioService
from backend.models.portfolio import PortfolioCreate

class TestPortfolioService:
    @pytest.fixture
    def portfolio_service(self):
        return PortfolioService()
    
    @pytest.fixture
    def sample_portfolio_data(self):
        return PortfolioCreate(
            name="Test Portfolio",
            initial_amount=10000.0,
            strategy_prompt="Test strategy",
            llm_provider="openai",
            llm_model="gpt-4"
        )
    
    async def test_create_portfolio_success(
        self, 
        portfolio_service, 
        sample_portfolio_data
    ):
        """Test successful portfolio creation."""
        with patch('backend.services.portfolio_service.save_portfolio_config') as mock_save:
            mock_save.return_value = True
            
            result = await portfolio_service.create_portfolio(sample_portfolio_data)
            
            assert result.name == "Test Portfolio"
            assert result.initial_amount == 10000.0
            mock_save.assert_called_once()
    
    async def test_create_portfolio_duplicate_name(
        self, 
        portfolio_service, 
        sample_portfolio_data
    ):
        """Test portfolio creation with duplicate name raises error."""
        with patch('backend.services.portfolio_service.portfolio_exists') as mock_exists:
            mock_exists.return_value = True
            
            with pytest.raises(ValidationError, match="Portfolio name already exists"):
                await portfolio_service.create_portfolio(sample_portfolio_data)
```

#### Frontend Testing

**Test Types**:
- Component unit tests
- Integration tests for API interactions
- E2E tests for user workflows

```javascript
// tests/unit/components/PortfolioCard.test.js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PortfolioCard from '@/components/PortfolioCard.vue'

describe('PortfolioCard', () => {
  const mockPortfolio = {
    name: 'Test Portfolio',
    totalValue: 15000,
    returnPct: 25.5
  }

  it('renders portfolio information correctly', () => {
    const wrapper = mount(PortfolioCard, {
      props: { portfolio: mockPortfolio }
    })

    expect(wrapper.find('.portfolio-name').text()).toBe('Test Portfolio')
    expect(wrapper.text()).toContain('$15,000')
    expect(wrapper.text()).toContain('+25.5%')
  })

  it('applies correct styling for positive returns', () => {
    const wrapper = mount(PortfolioCard, {
      props: { portfolio: mockPortfolio }
    })

    const returnElement = wrapper.find('.portfolio-return')
    expect(returnElement.classes()).toContain('text-green-500')
  })

  it('emits click event when clicked', async () => {
    const wrapper = mount(PortfolioCard, {
      props: { portfolio: mockPortfolio }
    })

    await wrapper.trigger('click')
    
    expect(wrapper.emitted('click')).toBeTruthy()
    expect(wrapper.emitted('click')[0][0]).toBe(mockPortfolio)
  })
})
```

### Documentation Requirements

All contributions should include appropriate documentation:

#### Code Documentation
- **Python**: Use docstrings following Google style
- **JavaScript/Vue**: Use JSDoc comments for complex functions
- **Inline Comments**: Explain complex logic, not obvious code

#### API Documentation
- Update OpenAPI specifications for new endpoints
- Include request/response examples
- Document error codes and responses

#### User Documentation
- Update user guide for new features
- Add screenshots for UI changes
- Include configuration examples

#### Developer Documentation
- Update architecture docs for structural changes
- Add troubleshooting information
- Include performance considerations

## Pull Request Process

### Before Submitting

1. **Run Tests**: Ensure all tests pass locally
2. **Check Code Style**: Run linters and formatters
3. **Update Documentation**: Include necessary documentation updates
4. **Review Your Changes**: Self-review your code for quality and clarity
5. **Rebase on Latest Main**: Ensure your branch is up to date

### PR Requirements

#### Pull Request Template

Your PR should include:

```markdown
## Description
Brief description of the changes and their purpose.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Related Issues
Fixes #123
Relates to #456

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] E2E tests added/updated
- [ ] Manual testing completed

## Screenshots (if applicable)
Include screenshots for UI changes.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No new warnings introduced
- [ ] Branch is up to date with main
- [ ] Commit messages follow conventional commits format

## Breaking Changes
List any breaking changes and migration steps required.

## Additional Notes
Any additional context or considerations.
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Peer Review**: At least one maintainer reviews the code
3. **Testing**: Reviewers may test the changes
4. **Feedback**: Address any review comments promptly
5. **Approval**: Maintainer approves the PR
6. **Merge**: Maintainer merges the approved PR

### Review Criteria

Reviewers will evaluate:

- **Functionality**: Does the code work as intended?
- **Code Quality**: Is the code well-written and maintainable?
- **Testing**: Is there adequate test coverage?
- **Documentation**: Are changes properly documented?
- **Performance**: Does it impact system performance?
- **Security**: Are there any security implications?
- **Breaking Changes**: Are breaking changes necessary and well-documented?

## Issue Reporting

### Bug Reports

Use the bug report template and include:

#### Environment Information
- Operating System and version
- Python version (for backend issues)
- Node.js version (for frontend issues)
- Browser and version (for UI issues)
- Docker version (if using containers)

#### Reproduction Steps
1. Clear, numbered steps to reproduce the issue
2. Expected behavior
3. Actual behavior
4. Screenshots or error messages (if applicable)

#### Additional Context
- Portfolio configurations that trigger the issue
- API key configuration status
- Recent changes made to the system
- Relevant log files or error messages

### Feature Requests

Use the feature request template and include:

- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How should it work?
- **Alternatives Considered**: What other approaches were considered?
- **Use Cases**: Who would benefit and how?
- **Implementation Notes**: Any technical considerations

### Security Issues

**Do not report security vulnerabilities in public issues.**

Instead:
1. Email security@fintrade.example.com (or create private issue if available)
2. Include detailed description of the vulnerability
3. Wait for acknowledgment before public disclosure
4. Allow reasonable time for fix before disclosure

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests, and technical discussions
- **GitHub Discussions**: General questions, ideas, and community discussions
- **Pull Requests**: Code review and collaboration
- **Documentation**: Comprehensive guides and references

### Getting Help

#### For Users
- Check the [User Guide](docs/USER_GUIDE.md)
- Search existing GitHub Issues
- Create a new issue with detailed information

#### For Developers
- Review the [Developer Guide](docs/DEVELOPER_GUIDE.md)
- Check the [Architecture Documentation](docs/ARCHITECTURE.md)
- Join GitHub Discussions for technical questions

#### For Contributors
- Read this contributing guide thoroughly
- Start with "good first issue" labeled issues
- Ask questions in GitHub Discussions
- Reach out to maintainers for guidance

### Recognition

We appreciate all contributions and will:

- **Acknowledge Contributors**: List contributors in release notes
- **Highlight Contributions**: Feature significant contributions in project updates
- **Provide Feedback**: Offer constructive feedback to help contributors grow
- **Mentor New Contributors**: Help newcomers get started with the project

### Governance

#### Maintainers

Current maintainers have:
- **Commit Access**: Can merge pull requests
- **Issue Triage**: Can label and assign issues
- **Release Authority**: Can create and publish releases
- **Moderation Powers**: Can enforce code of conduct

#### Decision Making

- **Minor Changes**: Maintainers can approve and merge
- **Major Changes**: Require discussion and consensus
- **Breaking Changes**: Need careful consideration and community input
- **Project Direction**: Discussed openly in GitHub Discussions

## License

By contributing to FinTradeAgent, you agree that your contributions will be licensed under the same license as the project (MIT License). You retain copyright of your contributions but grant the project maintainers the right to use and distribute your contributions as part of the project.

## Questions?

If you have questions about contributing, please:

1. Check this document and the [Developer Guide](docs/DEVELOPER_GUIDE.md)
2. Search existing GitHub Issues and Discussions
3. Create a new GitHub Discussion with the "Question" category
4. Reach out to maintainers if needed

Thank you for contributing to FinTradeAgent! Your contributions help make this project better for everyone in the trading and AI community. 🚀

---

*This contributing guide is a living document and will be updated as the project evolves. Feedback and suggestions for improvements are always welcome.*