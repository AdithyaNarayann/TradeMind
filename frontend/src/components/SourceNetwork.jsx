import { useState, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { 
  Link2, ChevronRight, Globe, Calendar, Shield, Filter
} from 'lucide-react';

// Helper to extract domain from URL
function extractDomain(url) {
  try {
    return new URL(url).hostname.replace('www.', '');
  } catch {
    return 'unknown';
  }
}

// Helper to calculate simple reputation score from domain
function getReputationFromDomain(domain) {
  const highRep = ['reuters.com', 'bbc.com', 'nytimes.com', 'washingtonpost.com', 
    'theguardian.com', 'ndtv.com', 'thehindu.com', 'cnn.com', 'apnews.com'];
  const medRep = ['indiatoday.in', 'news18.com', 'hindustantimes.com', 'timesofindia.indiatimes.com',
    'bloomberg.com', 'forbes.com', 'businessinsider.com'];
  const lowRep = ['reddit.com', 'twitter.com', 'x.com', 'facebook.com', 'youtube.com'];
  
  for (const d of highRep) if (domain.includes(d)) return { score: 90, tier: 'high' };
  for (const d of medRep) if (domain.includes(d)) return { score: 70, tier: 'medium' };
  for (const d of lowRep) if (domain.includes(d)) return { score: 30, tier: 'low' };
  return { score: 50, tier: 'unknown' };
}

// 3D Node Component
function SourceNode({ position, node, isHovered, onHover, onClick }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);
  
  const getNodeColor = (tier) => {
    const colors = {
      'high': '#14b8a6',
      'medium': '#fb923c',
      'low': '#ef4444',
      'unknown': '#94a3b8'
    };
    return colors[tier] || colors.unknown;
  };
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime + position[0]) * 0.1;
      const scale = hovered || isHovered ? 1.3 : 1;
      meshRef.current.scale.lerp({ x: scale, y: scale, z: scale }, 0.1);
    }
  });
  
  return (
    <mesh
      ref={meshRef}
      position={position}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHovered(true);
        onHover?.(node);
      }}
      onPointerOut={() => {
        setHovered(false);
        onHover?.(null);
      }}
      onClick={() => onClick?.(node)}
    >
      <sphereGeometry args={[0.15, 32, 32]} />
      <meshStandardMaterial 
        color={getNodeColor(node.tier)}
        emissive={getNodeColor(node.tier)}
        emissiveIntensity={hovered || isHovered ? 0.5 : 0.2}
        metalness={0.3}
        roughness={0.4}
      />
    </mesh>
  );
}

// 3D Edge Component
function NetworkEdge({ start, end }) {
  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={2}
          array={new Float32Array([...start, ...end])}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial color="#475569" opacity={0.4} transparent />
    </line>
  );
}

// 3D Graph Scene
function NetworkScene({ nodes, hoveredNode, onNodeHover, onNodeClick }) {
  const groupRef = useRef();
  
  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.002;
    }
  });
  
  // Calculate positions for nodes in a 3D space
  const nodePositions = useMemo(() => {
    if (!nodes || nodes.length === 0) return [];
    
    return nodes.map((node, idx) => {
      const angle = (idx / nodes.length) * Math.PI * 2;
      const radius = 1.5 + (node.score / 100) * 0.5;
      const height = (node.score - 50) / 50;
      
      return [
        Math.cos(angle) * radius,
        height,
        Math.sin(angle) * radius
      ];
    });
  }, [nodes]);
  
  // Create edges between adjacent nodes
  const edges = useMemo(() => {
    if (nodes.length < 2) return [];
    const result = [];
    for (let i = 0; i < nodes.length; i++) {
      const next = (i + 1) % nodes.length;
      result.push({ from: i, to: next });
    }
    // Add some cross connections
    if (nodes.length > 3) {
      result.push({ from: 0, to: Math.floor(nodes.length / 2) });
    }
    return result;
  }, [nodes]);
  
  return (
    <group ref={groupRef}>
      {/* Render edges */}
      {edges.map((edge, idx) => {
        const startPos = nodePositions[edge.from];
        const endPos = nodePositions[edge.to];
        if (startPos && endPos) {
          return <NetworkEdge key={idx} start={startPos} end={endPos} />;
        }
        return null;
      })}
      
      {/* Render nodes */}
      {nodes.map((node, idx) => (
        <SourceNode
          key={node.id}
          position={nodePositions[idx]}
          node={node}
          isHovered={hoveredNode?.id === node.id}
          onHover={onNodeHover}
          onClick={onNodeClick}
        />
      ))}
      
      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} />
    </group>
  );
}

// Source List Item
function SourceListItem({ source, isHovered, onHover }) {
  const getTierColor = (tier) => {
    const colors = {
      'high': 'bg-neo-teal',
      'medium': 'bg-neo-orange',
      'low': 'bg-red-500',
      'unknown': 'bg-gray-500'
    };
    return colors[tier] || colors.unknown;
  };
  
  return (
    <div 
      className={`
        p-3 border-b border-neo-navy/10 transition-colors cursor-pointer
        ${isHovered ? 'bg-neo-orange/10' : 'hover:bg-neo-cream/50'}
      `}
      onMouseEnter={() => onHover?.(source)}
      onMouseLeave={() => onHover?.(null)}
    >
      <div className="flex items-start gap-3">
        <div className={`w-3 h-3 rounded-full mt-1 ${getTierColor(source.tier)}`} />
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <p className="font-bold text-neo-navy text-sm truncate">{source.domain}</p>
            <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-gray-100 text-gray-600">
              Commentary
            </span>
          </div>
          
          <p className="text-xs text-neo-navy/70 line-clamp-2 mb-1">{source.title}</p>
          
          <div className="flex items-center gap-3 text-[10px] text-neo-navy/50">
            <span className="flex items-center gap-1">
              <Shield className="w-3 h-3" />
              {source.score}%
            </span>
          </div>
          
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-2 text-xs text-neo-teal hover:text-neo-orange transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            View source <ChevronRight className="w-3 h-3" />
          </a>
        </div>
        
        <div className={`
          w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold
          ${source.score >= 80 ? 'bg-neo-teal/20 text-neo-teal' :
            source.score >= 60 ? 'bg-neo-orange/20 text-neo-orange' :
            'bg-red-100 text-red-600'}
        `}>
          {source.score}
        </div>
      </div>
    </div>
  );
}

// Main SourceNetwork Component
export default function SourceNetwork({ webContext, onChainHash }) {
  const [hoveredNode, setHoveredNode] = useState(null);
  
  if (!webContext || !webContext.sources || webContext.sources.length === 0) {
    return null;
  }
  
  // Process simple sources into nodes with all needed fields
  const processedSources = useMemo(() => {
    return webContext.sources.map((source, idx) => {
      const domain = extractDomain(source.url);
      const rep = getReputationFromDomain(domain);
      return {
        id: `source_${idx}`,
        title: source.title,
        url: source.url,
        snippet: source.snippet,
        domain,
        score: rep.score,
        tier: rep.tier
      };
    });
  }, [webContext.sources]);
  
  const highCount = processedSources.filter(s => s.score >= 80).length;
  const medCount = processedSources.filter(s => s.score >= 50 && s.score < 80).length;
  const lowCount = processedSources.filter(s => s.score < 50).length;
  
  return (
    <div className="overflow-hidden border-[2px] border-neo-navy">
      {/* Header Stats Bar */}
      <div className="p-2 bg-neo-cream border-b-[2px] border-neo-navy flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Link2 className="w-4 h-4 text-neo-navy" />
          <span className="text-neo-navy/60">Sources:</span>
          <span className="font-bold text-neo-navy">{processedSources.length} analyzed</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-neo-navy" />
          <span className="text-neo-navy/60">Verified:</span>
          <span className="font-bold text-neo-navy">Now</span>
        </div>
        
        {onChainHash && (
          <div className="flex items-center gap-2 ml-auto">
            <Globe className="w-4 h-4 text-neo-teal" />
            <span className="text-neo-navy/60">On-chain:</span>
            <a 
              href={`https://sepolia.etherscan.io/tx/${onChainHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-neo-teal hover:underline"
            >
              {onChainHash.slice(0, 10)}...
            </a>
          </div>
        )}
      </div>
      
      {/* Main Content */}
      <div className="grid lg:grid-cols-5 divide-x-[2px] divide-neo-navy">
        {/* 3D Graph Panel */}
        <div className="lg:col-span-3 relative">
          <div className="p-2 border-b border-neo-navy/20 flex items-center justify-between bg-neo-navy/5">
            <span className="font-bold text-neo-navy text-sm">Source Network</span>
            <Filter className="w-4 h-4 text-neo-navy/40" />
          </div>
          
          {/* 3D Canvas */}
          <div className="h-[280px] bg-neo-navy relative">
            <Canvas camera={{ position: [0, 2, 5], fov: 50 }}>
              <color attach="background" args={['#1e293b']} />
              <fog attach="fog" args={['#1e293b', 5, 15]} />
              
              <NetworkScene 
                nodes={processedSources}
                hoveredNode={hoveredNode}
                onNodeHover={setHoveredNode}
                onNodeClick={(node) => {
                  if (node?.url) {
                    window.open(node.url, '_blank');
                  }
                }}
              />
              
              <OrbitControls 
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                autoRotate={false}
                minDistance={2}
                maxDistance={10}
              />
            </Canvas>
            
            {/* Controls hint */}
            <div className="absolute bottom-2 left-2 text-[10px] text-neo-cream/50 bg-neo-navy/50 px-2 py-1 rounded">
              <span className="text-neo-teal">Drag</span> to rotate · 
              <span className="text-neo-teal"> Scroll</span> to zoom
            </div>
            
            {/* Hovered node info */}
            {hoveredNode && (
              <div className="absolute top-2 left-2 bg-neo-cream p-2 rounded shadow-lg max-w-xs border-[2px] border-neo-navy">
                <p className="font-bold text-neo-navy text-sm">{hoveredNode.domain}</p>
                <p className="text-xs text-neo-navy/70 line-clamp-2 mt-1">{hoveredNode.title}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`
                    px-1.5 py-0.5 text-[10px] font-bold uppercase rounded
                    ${hoveredNode.score >= 80 ? 'bg-neo-teal/20 text-neo-teal' :
                      hoveredNode.score >= 50 ? 'bg-neo-orange/20 text-neo-orange' :
                      'bg-red-100 text-red-600'}
                  `}>
                    {hoveredNode.tier}
                  </span>
                  <span className="text-[10px] text-neo-navy/50">
                    {hoveredNode.score}% credibility
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Sources List Panel */}
        <div className="lg:col-span-2 flex flex-col">
          <div className="p-2 border-b border-neo-navy/20 bg-neo-navy/5">
            <span className="font-bold text-neo-navy text-sm">
              Sources ({processedSources.length})
            </span>
          </div>
          
          <div className="flex-1 overflow-y-auto max-h-[280px]">
            {processedSources.map((source) => (
              <SourceListItem
                key={source.id}
                source={source}
                isHovered={hoveredNode?.id === source.id}
                onHover={setHoveredNode}
              />
            ))}
          </div>
        </div>
      </div>
      
      {/* Credibility Summary */}
      <div className="p-2 bg-neo-navy/5 border-t border-neo-navy/20 flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neo-teal" />
          <span className="text-neo-navy/70">High:</span>
          <span className="font-bold text-neo-teal">{highCount}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neo-orange" />
          <span className="text-neo-navy/70">Medium:</span>
          <span className="font-bold text-neo-orange">{medCount}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-neo-navy/70">Low:</span>
          <span className="font-bold text-red-500">{lowCount}</span>
        </div>
      </div>
    </div>
  );
}
