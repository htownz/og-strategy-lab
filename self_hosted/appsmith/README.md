# Appsmith Integration for OG Strategy Lab

This directory contains files for integrating Appsmith with OG Strategy Lab for custom UI building.

## Setup Instructions

1. Start the self-hosted environment:
   ```bash
   cd ..
   ./setup.sh
   ```

2. Access Appsmith at http://localhost:8080

3. Create a new account or use the default admin credentials

4. Import the application:
   - Go to "Applications" > "Import" > "Import from file"
   - Select the `og_strategy_lab_app.json` file
   - Click "Import"

5. Configure the database connection:
   - Go to the imported application
   - Navigate to "Data Sources"
   - Update the PostgreSQL connection details if necessary
   - Test the connection

6. Start building your custom UI!

## Customization Ideas

1. **Signal Dashboard**: Visualize real-time signals with filtering by strategy and timeframe
2. **Strategy Builder**: Create a drag-and-drop interface for building custom strategies
3. **Performance Analytics**: Build interactive charts for performance tracking
4. **Admin Panel**: Create an admin interface for system management
5. **User Reports**: Generate customized reports for strategies and signals

## Resources

- [Appsmith Documentation](https://docs.appsmith.com/)
- [PostgreSQL Integration Guide](https://docs.appsmith.com/reference/datasources/querying-postgres)
- [Custom Widgets Guide](https://docs.appsmith.com/reference/widgets)
