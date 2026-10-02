import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import {
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material';
import { type FormEvent, useState } from 'react';

import { useAppDispatch, useAppSelector } from './app/hooks';
import { useAddItemMutation, useGetHealthQuery, useGetItemsQuery } from './features/api/apiSlice';
import { decrement, increment } from './features/counter/counterSlice';

const TIERS = ['S', 'A', 'B', 'C', 'D'];

function BackendStatus() {
  const { data, isLoading, isError } = useGetHealthQuery();

  if (isLoading) return <Chip label="Backend : connexion…" />;
  if (isError || data?.status !== 'ok') return <Chip color="error" label="Backend : hors ligne" />;
  return <Chip color="success" label="Backend : en ligne" />;
}

function ItemsCard() {
  const { data: items = [], isError } = useGetItemsQuery();
  const [addItem, { isLoading }] = useAddItemMutation();
  const [name, setName] = useState('');
  const [tier, setTier] = useState('C');

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    await addItem({ name: name.trim(), tier });
    setName('');
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Items (RTK Query)
        </Typography>
        <Stack component="form" direction="row" spacing={2} onSubmit={handleSubmit}>
          <TextField
            label="Nom"
            size="small"
            value={name}
            onChange={(e) => setName(e.target.value)}
            fullWidth
          />
          <TextField
            select
            label="Tier"
            size="small"
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            sx={{ minWidth: 90 }}
          >
            {TIERS.map((t) => (
              <MenuItem key={t} value={t}>
                {t}
              </MenuItem>
            ))}
          </TextField>
          <Button type="submit" variant="contained" disabled={isLoading}>
            Ajouter
          </Button>
        </Stack>
        {isError ? (
          <Typography color="error" sx={{ mt: 2 }}>
            Impossible de charger les items : le backend est-il lancé ?
          </Typography>
        ) : (
          <List dense>
            {items.map((item) => (
              <ListItem key={item.id}>
                <Chip label={item.tier} size="small" color="primary" sx={{ mr: 2 }} />
                <ListItemText primary={item.name} />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
}

function CounterCard() {
  const count = useAppSelector((state) => state.counter.value);
  const dispatch = useAppDispatch();

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Compteur (slice Redux)
        </Typography>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
          <IconButton aria-label="Décrémenter" onClick={() => dispatch(decrement())}>
            <RemoveIcon />
          </IconButton>
          <Typography variant="h5">{count}</Typography>
          <IconButton aria-label="Incrémenter" onClick={() => dispatch(increment())}>
            <AddIcon />
          </IconButton>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function App() {
  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            TierList
          </Typography>
          <BackendStatus />
        </Toolbar>
      </AppBar>
      <Container maxWidth="md">
        <Box sx={{ py: 4 }}>
          <Stack spacing={3}>
            <ItemsCard />
            <CounterCard />
          </Stack>
        </Box>
      </Container>
    </>
  );
}
