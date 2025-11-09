import { useState } from 'react';
import { IconButton, Badge, Popover } from '@mui/material';
import { Notifications } from '@mui/icons-material';
import { useAppSelector } from '../../store/hooks';
import NotificationDropdown from './NotificationDropdown';

export default function NotificationBell() {
  const { unreadCount } = useAppSelector((state) => state.notification);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);

  return (
    <>
      <IconButton color="inherit" onClick={handleClick}>
        <Badge badgeContent={unreadCount} color="error">
          <Notifications />
        </Badge>
      </IconButton>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <NotificationDropdown onClose={handleClose} />
      </Popover>
    </>
  );
}
