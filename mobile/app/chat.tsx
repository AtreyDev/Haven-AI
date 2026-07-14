/**
 * Harbor LifeLine — chat.tsx (Distress Interface)
 * Per blueprint section 5: "Amber bubbles (AI), Gray bubbles (User).
 * Displays Hub latency." Also integrates expo-speech TTS per "Voice
 * Features" — crucial for injured hands or low-visibility scenarios.
 */

import React, { useCallback, useRef, useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import * as Speech from "expo-speech";
import { colors, fonts, spacing, radii } from "../theme/tokens";
import { useHarborStore, type ChatMessage } from "../store/useHarborStore";
import { HubClient, DEFAULT_HUB_URL } from "../lib/hubClient";
import { mirrorMessage } from "../lib/localLog";

const hubClient = new HubClient(DEFAULT_HUB_URL);

export default function Chat() {
  const messages = useHarborStore((s) => s.messages);
  const addMessage = useHarborStore((s) => s.addMessage);
  const isSending = useHarborStore((s) => s.isSending);
  const setSending = useHarborStore((s) => s.setSending);
  const connection = useHarborStore((s) => s.connection);

  const [draft, setDraft] = useState("");
  const listRef = useRef<FlatList<ChatMessage>>(null);

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || isSending) return;

    setDraft("");

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      text,
      timestamp: Date.now(),
    };
    addMessage(userMsg);
    mirrorMessage(userMsg).catch(() => {
      /* local mirror is best-effort; never block the SOS flow on it */
    });

    setSending(true);
    try {
      const result = await hubClient.ask(text, "mobile-client", "Distress Node");

      const aiMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "ai",
        text: result.response,
        timestamp: Date.now(),
        source: result.source,
        latencyMs: result.latency_ms,
      };
      addMessage(aiMsg);
      mirrorMessage(aiMsg).catch(() => {});

      // Crucial for injured hands or low-visibility scenarios.
      Speech.speak(result.response, { rate: 0.95 });
    } catch (err) {
      const fallback: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "ai",
        text: "Insufficient data — conserve energy and wait. (Could not reach Hub.)",
        timestamp: Date.now(),
      };
      addMessage(fallback);
      Speech.speak(fallback.text, { rate: 0.95 });
    } finally {
      setSending(false);
      requestAnimationFrame(() => listRef.current?.scrollToEnd({ animated: true }));
    }
  }, [draft, isSending, addMessage, setSending]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>DISTRESS CHANNEL</Text>
        <Text style={styles.headerSub}>{connection.toUpperCase()}</Text>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={80}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          contentContainerStyle={styles.messageList}
          renderItem={({ item }) => <Bubble message={item} />}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        />

        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={draft}
            onChangeText={setDraft}
            placeholder="Describe your emergency..."
            placeholderTextColor={colors.textMuted}
            multiline
            editable={!isSending}
          />
          <Pressable
            style={[styles.sendButton, isSending && styles.sendButtonDisabled]}
            onPress={send}
            disabled={isSending}
          >
            <Text style={styles.sendButtonText}>{isSending ? "..." : "SEND"}</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isAi = message.role === "ai";
  return (
    <View style={[styles.bubbleRow, isAi ? styles.bubbleRowLeft : styles.bubbleRowRight]}>
      <View style={[styles.bubble, isAi ? styles.bubbleAi : styles.bubbleUser]}>
        <Text style={[styles.bubbleText, isAi ? styles.bubbleTextAi : styles.bubbleTextUser]}>
          {message.text}
        </Text>
        {isAi && message.latencyMs !== undefined ? (
          <Text style={styles.latencyText}>
            {message.source === "kb" ? "KB-INSTANT" : "AI-INFERRED"} · {message.latencyMs}ms
          </Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTitle: {
    color: colors.textPrimary,
    fontFamily: fonts.monoBold,
    fontSize: 14,
    letterSpacing: 1,
  },
  headerSub: {
    color: colors.amber,
    fontFamily: fonts.monoMedium,
    fontSize: 11,
  },
  messageList: {
    padding: spacing.md,
    gap: spacing.sm,
  },
  bubbleRow: { flexDirection: "row", marginVertical: spacing.xs },
  bubbleRowLeft: { justifyContent: "flex-start" },
  bubbleRowRight: { justifyContent: "flex-end" },
  bubble: {
    maxWidth: "82%",
    borderRadius: radii.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  bubbleAi: {
    backgroundColor: colors.bubbleAI,
    borderBottomLeftRadius: radii.sm,
  },
  bubbleUser: {
    backgroundColor: colors.bubbleUser,
    borderBottomRightRadius: radii.sm,
  },
  bubbleText: {
    fontFamily: fonts.mono,
    fontSize: 14,
    lineHeight: 20,
  },
  bubbleTextAi: { color: colors.bubbleAIText },
  bubbleTextUser: { color: colors.bubbleUserText },
  latencyText: {
    marginTop: spacing.xs,
    color: colors.background,
    opacity: 0.6,
    fontFamily: fonts.monoMedium,
    fontSize: 10,
  },
  inputRow: {
    flexDirection: "row",
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: spacing.sm,
  },
  input: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    fontFamily: fonts.mono,
    fontSize: 14,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    maxHeight: 100,
  },
  sendButton: {
    backgroundColor: colors.amber,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    justifyContent: "center",
  },
  sendButtonDisabled: {
    backgroundColor: colors.amberDim,
  },
  sendButtonText: {
    color: colors.background,
    fontFamily: fonts.monoBold,
    fontSize: 13,
  },
});
