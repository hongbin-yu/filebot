/**
 * 组件配置对话框
 */

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Button,
  Box,
} from '@mui/material';
import { Close, Settings } from '@mui/icons-material';
import { useEditorState } from '../../hooks/useEditorState';
import ComponentConfig from './ComponentConfig';

const ComponentConfigDialog: React.FC = () => {
  const { configDialogOpen, closeConfigDialog, selectedInstance } = useEditorState();

  // 如果没有选中的组件，对话框仍然可以打开，但内容为空
  // 实际上，通常应该在选中组件时才打开对话框

  return (
    <Dialog
      open={configDialogOpen}
      onClose={closeConfigDialog}
      maxWidth="md"
      fullWidth
      sx={{
        '& .MuiDialog-paper': {
          maxHeight: '90vh',
          height: 'auto',
          minHeight: '500px',
        },
      }}
    >
      {/* 对话框标题栏 */}
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: selectedInstance ? 'primary.50' : 'background.paper',
          p: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Settings color="primary" />
          <span>组件配置</span>
          {selectedInstance && (
            <Box sx={{ ml: 2, display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.875rem', color: 'text.secondary' }}>
                {selectedInstance.template_id}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                实例ID: {selectedInstance.id.slice(0, 8)}...
              </span>
            </Box>
          )}
        </Box>
        <IconButton
          aria-label="close"
          onClick={closeConfigDialog}
          size="small"
          sx={{
            color: 'text.secondary',
            '&:hover': { color: 'text.primary' },
          }}
        >
          <Close />
        </IconButton>
      </DialogTitle>

      {/* 对话框内容 - 使用原有的ComponentConfig */}
      <DialogContent sx={{ p: 0, overflow: 'auto' }}>
        <Box sx={{ height: '100%', overflow: 'visible' }}>
          <ComponentConfig asDialogContent={true} />
        </Box>
      </DialogContent>

      {/* 对话框操作按钮 */}
      <DialogActions
        sx={{
          borderTop: 1,
          borderColor: 'divider',
          p: 2,
          justifyContent: 'space-between',
        }}
      >
        <Box>
          <Button size="small" color="inherit" onClick={closeConfigDialog}>
            取消
          </Button>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() => {
              // 重置配置的占位函数
              console.log('重置配置');
            }}
          >
            重置
          </Button>
          <Button size="small" variant="contained" onClick={closeConfigDialog}>
            应用更改
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
};

export default ComponentConfigDialog;
