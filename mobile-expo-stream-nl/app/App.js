import React, { useState, useRef } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, SafeAreaView, KeyboardAvoidingView, Platform } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { WebView } from 'react-native-webview';
import { sendToAgent, callIntent } from './api';

export default function App() {
  const [msgs, setMsgs] = useState([{ id:'hello', who:'agent', txt:'Hoi! Ik ben AeonCore. Deel je idee en ik help je met specificaties, code en visuals.' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showWeb, setShowWeb] = useState(false);
  const [webHTML, setWebHTML] = useState('');
  const listRef = useRef(null);

  const addMsg = (who, txt, extra = {}) => {
    const m = { id: String(Date.now())+Math.random(), who, txt, ...extra };
    setMsgs(prev => [...prev, m]);
    setTimeout(() => listRef.current?.scrollToEnd({ animated:true }), 50);
  };

  // Eerdere berichten gaan mee, zodat AeonCore het gesprek onthoudt.
  // Intent-berichten ([SPEC] e.d.) en de begroeting tellen niet mee.
  const buildHistory = () => msgs
    .filter(m => m.id !== 'hello' && !m.intent && !m.error && m.txt)
    .slice(-20)
    .map(m => ({ role: m.who === 'user' ? 'user' : 'assistant', content: m.txt }));

  const onSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    const history = buildHistory();
    addMsg('user', text);
    setInput('');
    setLoading(true);
    try {
      const reply = await sendToAgent(text, history);
      addMsg('agent', reply);
    } catch(e) {
      addMsg('agent', '⚠️ ' + e.message, { error:true });
    } finally {
      setLoading(false);
    }
  };

  const wrapHTML = (inner) => `<!doctype html><html><head>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <script src='https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js'></script>
    <script>mermaid.initialize({startOnLoad:true});</script>
    <style>body{background:#0b0f12;color:#e6eef6;font-family:system-ui;padding:12px}</style>
  </head><body>${inner}</body></html>`;

  const onIntent = async (k) => {
    if (loading) return;
    const idea = input.trim() || 'Laat een klein NL voorbeeld zien.';
    addMsg('user', '['+k.toUpperCase()+'] '+idea, { intent:true });
    setInput('');
    setLoading(true);
    try {
      const data = await callIntent(k, idea);
      if (data.type === 'html') {
        setWebHTML(wrapHTML(data.content));
        setShowWeb(true);
        addMsg('agent', 'Ik heb een visual geopend.', { intent:true });
      } else {
        addMsg('agent', String(data.content), { intent:true });
      }
    } catch(e) {
      addMsg('agent', '⚠️ ' + e.message, { intent:true, error:true });
    } finally {
      setLoading(false);
    }
  };

  const quick = [{t:'Spec',k:'spec'},{t:'Code',k:'code'},{t:'Visual',k:'visualize'}];

  return (
    <SafeAreaView style={{flex:1, backgroundColor:'#0b0f12'}}>
      <StatusBar style="light" />
      <View style={{padding:14}}>
        <Text style={{color:'#e7fff6', fontWeight:'700', fontSize:18}}>Dynamik • AeonCore (NL)</Text>
        <Text style={{color:'#9bbec7', fontSize:12}}>Bouw ideeën • Specificaties • Code • Visuals</Text>
      </View>

      <FlatList ref={listRef} data={msgs} keyExtractor={(it)=>it.id}
        renderItem={({item}) => (
          <View style={{paddingHorizontal:14, marginBottom:8, flexDirection:'row', justifyContent:item.who==='user'?'flex-end':'flex-start'}}>
            <View style={{maxWidth:'80%', backgroundColor:item.who==='user'?'#059669':'#16202b', padding:12, borderRadius:14}}>
              <Text style={{color:'#e6eef6'}}>{item.txt}</Text>
            </View>
          </View>
        )}
        contentContainerStyle={{paddingBottom:8}}
      />

      {loading ? <Text style={{color:'#b9c6d1', textAlign:'center'}}>AeonCore denkt…</Text> : null}

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={{flexDirection:'row', gap:8, paddingHorizontal:14, paddingBottom:8, alignItems:'center'}}>
          <TextInput style={{flex:1, backgroundColor:'#06111a', color:'#fff', padding:12, borderRadius:10, borderColor:'#1b2a35', borderWidth:1}} placeholder="Typ je idee…" placeholderTextColor="#7a8b9a" value={input} onChangeText={setInput} onSubmitEditing={onSend} returnKeyType="send" />
          <TouchableOpacity onPress={onSend} style={{backgroundColor:'#059669', paddingVertical:10, paddingHorizontal:16, borderRadius:10}}>
            <Text style={{color:'#fff', fontWeight:'700'}}>Stuur</Text>
          </TouchableOpacity>
        </View>
        <View style={{flexDirection:'row', gap:8, paddingHorizontal:14, paddingBottom:12}}>
          {quick.map(q => (
            <TouchableOpacity key={q.k} onPress={()=>onIntent(q.k)} style={{backgroundColor:'#0f1720', paddingVertical:8, paddingHorizontal:12, borderRadius:10, borderWidth:1, borderColor:'#1b2a35'}}>
              <Text style={{color:'#9bbec7', fontSize:12}}>{q.t}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </KeyboardAvoidingView>

      {showWeb && (
        <View style={{position:'absolute', top:0,left:0,right:0,bottom:0, backgroundColor:'#000C'}}>
          <TouchableOpacity onPress={()=>setShowWeb(false)} style={{padding:10, alignSelf:'flex-end'}}><Text style={{color:'#fff'}}>Sluiten ✖</Text></TouchableOpacity>
          <WebView originWhitelist={['*']} source={{ html: webHTML }} />
        </View>
      )}
    </SafeAreaView>
  );
}
