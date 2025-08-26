# MCP MySQL Operations Server - Comprehensive Usage Guide

## Overview

You are working with the **MCP MySQL Operations Server**, a powerful tool that provides comprehensive MySQL database monitoring and analysis capabilities through natural language queries. This server offers **19 specialized tools** for database administration, performance monitoring, and system analysis.

## Core Capabilities

### 🔍 **Database Exploration & Schema Analysis**
- **Server Information**: Get MySQL version, configuration, and system status
- **Database Management**: List databases, analyze sizes and storage usage  
- **Schema Analysis**: Detailed table structures, indexes, constraints, and relationships
- **User Management**: MySQL user accounts, privileges, and security analysis

### 📊 **Performance Monitoring & Analysis**
- **Connection Monitoring**: Active sessions, process lists, and connection analysis
- **Performance Metrics**: Server status variables and performance counters
- **Storage Analysis**: Table sizes, index usage, and storage efficiency
- **Resource Utilization**: Database capacity planning and optimization insights
- **Performance Schema Integration**: Advanced query monitoring and I/O statistics

### 🎯 **Multi-Database Support**
All tools support the `database_name` parameter, allowing analysis across multiple databases from a single server instance.

---

## Available Tools (19 Tools)

### **Core Database Tools (11 Tools)**

### 1. **get_server_info**
**Purpose**: Display MySQL server version, configuration status, and system information
**Usage**: "Show MySQL server information and version details"
**Features**: Server version, system variables, configuration status, Performance Schema availability

### 2. **get_database_list** 
**Purpose**: List all databases with sizes, character sets, and storage information
**Usage**: "List all databases and their storage usage"
**Features**: Database sizes, character sets, collations, table counts, storage distribution

### 3. **get_table_list**
**Purpose**: Display tables within a database with metadata and statistics
**Usage**: "Show all tables in the ecommerce database"
**Features**: Table information, storage engines, row counts, creation dates
**Required**: `database_name` parameter

### 4. **get_table_schema_info**
**Purpose**: Detailed schema information for specific tables or entire databases
**Usage**: "Analyze the schema structure of the customers table in ecommerce database"
**Features**: Column details, data types, indexes, constraints, foreign keys
**Required**: `database_name` parameter
**Optional**: `table_name` (leave empty for all tables)

### 5. **get_database_overview**
**Purpose**: Comprehensive database summary with table counts and storage statistics  
**Usage**: "Get overview of the test_ecommerce database structure and size"
**Features**: Database summary, table statistics, storage overview, schema analysis
**Required**: `database_name` parameter

### 6. **get_user_list**
**Purpose**: Display MySQL user accounts, privileges, and security information
**Usage**: "List all MySQL users and their privileges"
**Features**: User accounts, host patterns, privileges, account status, authentication methods

### 7. **get_active_connections**
**Purpose**: Monitor active database connections and session information
**Usage**: "Show current active connections and their details"
**Features**: Active connections, process list, session details, connection statistics
**Optional**: `user_filter`, `db_filter` for targeted monitoring

### 8. **get_server_status**
**Purpose**: Display MySQL server status variables and performance counters
**Usage**: "Show MySQL server performance metrics and status"
**Features**: Status variables, performance counters, resource utilization, operational metrics
**Optional**: `search_term` for filtering specific metrics

### 9. **get_table_size_info**
**Purpose**: Analyze table and index sizes with storage efficiency metrics
**Usage**: "Show table sizes and storage usage for the ecommerce database"
**Features**: Table sizes, index sizes, data/index ratios, storage efficiency analysis
**Required**: `database_name` parameter

### 10. **get_database_size_info**
**Purpose**: Database-level storage analysis and capacity planning
**Usage**: "Analyze database storage usage and capacity"
**Features**: Database sizes, storage distribution, capacity planning, growth analysis

### 11. **get_index_usage_stats**
**Purpose**: Index statistics, usage patterns, and optimization recommendations
**Usage**: "Analyze index usage and efficiency for the ecommerce database"
**Features**: Index statistics, cardinality, selectivity, usage patterns, optimization suggestions
**Required**: `database_name` parameter

### **Performance Schema Tools (8 Additional Tools)**

### 12. **get_mysql_config**
**Purpose**: Display MySQL configuration variables and system settings
**Usage**: "Show MySQL configuration settings and variables"
**Features**: Configuration variables, system settings, performance tuning options
**Optional**: `search_term` for filtering specific config options

### 13. **get_slow_queries** 
**Purpose**: Performance Schema-based slow query analysis and monitoring
**Usage**: "Show slow queries and performance bottlenecks"
**Features**: Slow query identification, execution statistics, performance insights
**Enhanced**: MySQL 8.0+ with improved Performance Schema tables

### 14. **get_table_io_stats**
**Purpose**: Table I/O statistics and access pattern analysis
**Usage**: "Analyze table I/O performance and access patterns"
**Features**: I/O statistics, read/write patterns, table access analysis
**Enhanced**: Performance Schema I/O monitoring capabilities

### 15. **get_lock_monitoring**
**Purpose**: Lock analysis, contention monitoring, and blocking session detection
**Usage**: "Monitor database locks and detect blocking sessions"
**Features**: Lock analysis, contention detection, blocking session identification
**Enhanced**: Performance Schema lock monitoring

### 16. **get_all_databases_tables**
**Purpose**: Cross-database table overview and comprehensive analysis
**Usage**: "Show all tables across all databases with their metadata"
**Features**: Multi-database table listing, storage engine analysis, comprehensive overview
**Optional**: `table_type` for filtering specific table types

### 17. **get_all_databases_table_sizes**
**Purpose**: Global table size analysis across all databases
**Usage**: "Show largest tables across all databases by size"
**Features**: Global size analysis, cross-database storage comparison, capacity insights
**Optional**: `limit` for controlling result count

### 18. **get_connection_info**
**Purpose**: Enhanced connection details and session monitoring
**Usage**: "Get detailed connection information and session statistics"
**Features**: Connection details, session information, connection pool analysis

### 19. **get_current_database_info**
**Purpose**: Current database context and active connection details
**Usage**: "Show information about the current database connection"
**Features**: Active database information, connection context, session details

---

## Version Compatibility

### ✅ **MySQL 8.0+ (Recommended)**
- **Full Feature Support**: All 19 tools with enhanced capabilities
- **Performance Schema**: Advanced monitoring and statistics with 8 dedicated Performance Schema tools
- **JSON Support**: Enhanced JSON functions and indexing
- **Security Features**: Role-based access control and improved security

### ✅ **MySQL 5.7 (Supported)**  
- **Core Functionality**: 11 core tools fully supported
- **Performance Schema**: Basic Performance Schema capabilities (limited features for 8 advanced tools)
- **Standard Features**: Full Information Schema support and basic monitoring

### ✅ **MySQL 5.7+ (Compatible)**
- **Core Functionality**: All 11 tools with standard features
- **Basic Performance Schema**: Standard monitoring capabilities
- **Information Schema**: Complete metadata access
- **Standard Features**: Full compatibility with core monitoring functions

---

## Query Patterns & Examples

### 🔍 **Exploratory Analysis**
Use these patterns to understand your database structure and status:

```
"What databases exist and how much storage do they use?"
"Show me the MySQL server version and configuration status"
"List all tables in the ecommerce database with their sizes"
"Display the schema structure of the customers table"
"What users exist and what are their privileges?"
```

### 📊 **Performance Monitoring**
Monitor database performance and identify optimization opportunities:

```
"Show current active connections and their activity"
"Display MySQL server performance metrics and status"
"Which tables are using the most storage space?"
"Analyze index usage and efficiency in the ecommerce database"
"What are the current server status variables?"
```

### 🎯 **Capacity Planning**
Understand storage usage and plan for growth:

```
"Show database storage usage across all databases"
"Which tables have grown the most in size?"
"Analyze storage efficiency and data/index ratios"
"Display comprehensive size analysis for the inventory database"
```

### 🔧 **Administration & Maintenance**
Administrative tasks and system analysis:

```
"Show all MySQL users and their host permissions"
"Display detailed schema information for the analytics database"
"What is the current connection status and process list?"
"Analyze table structures and relationships in the hr database"
```

---

## Best Practices

### 🎯 **Effective Query Formulation**
- **Be Specific**: Include database names when analyzing specific databases
- **Use Natural Language**: Ask questions as you would to a database administrator
- **Request Context**: Ask for explanations and recommendations along with data
- **Combine Analysis**: Request multiple related metrics in a single query

### 📊 **Performance Considerations**
- **Use Limits**: Most tools support `limit` parameters to control result size
- **Target Analysis**: Specify database names to focus analysis on relevant data
- **Peak Hours**: Consider running comprehensive analysis during off-peak hours
- **Regular Monitoring**: Use these tools regularly for proactive database management

### 🔒 **Security Guidelines**
- **Read-Only Operations**: All tools are designed for monitoring only - no data modification
- **Privilege Awareness**: Some tools require specific MySQL privileges for complete information
- **Sensitive Data**: Connection passwords and sensitive configuration details are automatically masked

---

## Advanced Usage Scenarios

### 🏢 **Multi-Database Environments**
Perfect for organizations managing multiple MySQL databases:
- Cross-database size comparisons
- Standardized schema analysis across environments
- Centralized user and permission auditing
- Comprehensive storage utilization tracking

### 🚀 **Performance Optimization**
Use these tools to identify and resolve performance issues:
- Index usage analysis and optimization recommendations
- Storage efficiency evaluation and improvement suggestions
- Connection pattern analysis for capacity planning
- Server configuration assessment and tuning guidance

### 📈 **Capacity Planning**
Strategic database growth management:
- Historical storage usage tracking
- Growth rate analysis and projections
- Resource utilization assessment
- Infrastructure scaling recommendations

### 🔍 **Compliance & Auditing**
Security and compliance monitoring:
- User access pattern analysis
- Privilege escalation detection
- Schema change tracking
- Security configuration assessment

---

## Troubleshooting Guide

### 🔧 **Common Issues**
- **Access Denied**: Ensure user has SELECT privileges on target databases
- **Performance Schema Unavailable**: Check `performance_schema = ON` in MySQL configuration
- **Information Schema Timeout**: Consider setting `information_schema_stats_expiry = 0` for real-time stats
- **Large Result Sets**: Use `limit` parameters to control output size

### 💡 **Optimization Tips**
- **Connection Efficiency**: Use connection pooling for frequent analysis
- **Query Performance**: Target specific databases rather than server-wide analysis when possible
- **Resource Management**: Monitor server load when running comprehensive analysis
- **Statistics Freshness**: Balance between real-time accuracy and performance impact

---

## Integration Examples

### 🤖 **AI Assistant Integration**
Perfect for integration with AI assistants like Claude, GPT, and other MCP-compatible tools:
- Natural language database exploration
- Automated performance analysis and reporting
- Intelligent capacity planning recommendations
- Conversational database administration support

### 📊 **Monitoring Dashboards**
Integrate with monitoring and visualization tools:
- Real-time database health monitoring
- Historical storage growth tracking
- Performance metric visualization
- Alert generation for threshold breaches

### 🔄 **Automation Workflows**
Incorporate into automated database management workflows:
- Scheduled health checks and reporting
- Capacity threshold monitoring and alerting
- Performance baseline establishment and tracking
- Change detection and impact analysis

---

This comprehensive MySQL operations server provides everything needed for professional database monitoring, analysis, and management through intuitive natural language queries.
