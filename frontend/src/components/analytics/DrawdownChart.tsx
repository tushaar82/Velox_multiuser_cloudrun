import { Card, CardContent, Typography, Box } from '@mui/material';
import Plot from 'react-plotly.js';
import type { EquityPoint } from '../../types';

interface DrawdownChartProps {
  data: EquityPoint[];
  title?: string;
}

export default function DrawdownChart({ data, title = 'Drawdown Analysis' }: DrawdownChartProps) {
  const timestamps = data.map(point => point.timestamp);
  const drawdown = data.map(point => point.drawdown * 100); // Convert to percentage

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
                y: drawdown,
                type: 'scatter',
                mode: 'lines',
                name: 'Drawdown',
                line: { color: '#d32f2f', width: 2 },
                fill: 'tozeroy',
                fillcolor: 'rgba(211, 47, 47, 0.2)',
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
                title: { text: 'Drawdown (%)' },
                tickformat: '.2f',
                range: [Math.min(...drawdown, 0) * 1.1, 0],
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
