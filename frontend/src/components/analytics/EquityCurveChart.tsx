import { Card, CardContent, Typography, Box } from '@mui/material';
import Plot from 'react-plotly.js';
import type { EquityPoint } from '../../types';

interface EquityCurveChartProps {
  data: EquityPoint[];
  title?: string;
}

export default function EquityCurveChart({ data, title = 'Equity Curve' }: EquityCurveChartProps) {
  const timestamps = data.map(point => point.timestamp);
  const equity = data.map(point => point.equity);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Box sx={{ width: '100%', height: 400 }}>
          <Plot
            data={[
              {
                x: timestamps,
                y: equity,
                type: 'scatter',
                mode: 'lines',
                name: 'Equity',
                line: { color: '#1976d2', width: 2 },
                fill: 'tozeroy',
                fillcolor: 'rgba(25, 118, 210, 0.1)',
              } as any,
            ]}
            layout={{
              autosize: true,
              margin: { l: 60, r: 30, t: 30, b: 60 },
              xaxis: {
                title: { text: 'Date' },
                type: 'date',
              },
              yaxis: {
                title: { text: 'Equity (₹)' },
                tickformat: ',.0f',
              },
              hovermode: 'x unified',
              showlegend: false,
            }}
            config={{
              responsive: true,
              displayModeBar: false,
            }}
            style={{ width: '100%', height: '100%' }}
          />
        </Box>
      </CardContent>
    </Card>
  );
}
